from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from backend.services import video_studio_captions, video_studio_planner
from render.animated_overlay import capture_html_keyframe as _capture_html_keyframe
from render.animated_overlay import render_alpha_webm


_ACTIVE_WORKS: set[str] = set()
_ACTIVE_LOCK = threading.RLock()
_FRAME_RATE = 24
_WIDTH = 1920
_HEIGHT = 1080


def _render_env() -> Dict[str, str]:
    """Return the environment used by every local render subprocess.

    launchd starts the preview service with a deliberately small PATH.  Homebrew
    and manually-installed macOS binaries normally live outside that PATH, so
    discover their standard locations here instead of relying on the shell that
    originally started the service.
    """
    env = dict(os.environ)
    candidates = [
        os.path.abspath(os.path.expanduser(env.get("SMART_SLIDES_TOOL_DIR", "~/.codex/smart-slides/bin"))),
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ]
    # Preserve an explicit tool directory as the highest-priority override,
    # while only adding directories that actually exist.  This does not install
    # or download a renderer.
    prefix: List[str] = []
    for candidate in candidates:
        if os.path.isdir(candidate) and candidate not in prefix:
            prefix.append(candidate)
    existing_path = [entry for entry in env.get("PATH", "").split(os.pathsep) if entry]
    env["PATH"] = os.pathsep.join([*prefix, *[entry for entry in existing_path if entry not in prefix]])
    return env


def _binary(name: str) -> str:
    resolved = shutil.which(name, path=_render_env().get("PATH"))
    return resolved or ""


def _safe_html(raw: Any) -> str:
    value = str(raw or "")
    value = re.sub(r"<\s*(script|iframe|object|embed)\b[^>]*>.*?<\s*/\s*\1\s*>", "", value, flags=re.I | re.S)
    value = re.sub(r"<\s*/?\s*(script|iframe|object|embed)\b[^>]*>", "", value, flags=re.I | re.S)
    value = re.sub(r"\s(?:src|srcset|href|xlink:href)\s*=\s*(['\"])(?:https?:)?//.*?\1", "", value, flags=re.I | re.S)
    value = re.sub(r"\s(?:src|srcset|href|xlink:href)\s*=\s*(?:https?:)?//[^\s>]+", "", value, flags=re.I)
    value = re.sub(r"\son\w+\s*=\s*(['\"]).*?\1", "", value, flags=re.I | re.S)
    value = re.sub(r"\son\w+\s*=\s*[^\s>]+", "", value, flags=re.I)
    return re.sub(r"url\(\s*(['\"]?)(?:https?:)?//.*?\1\s*\)", "none", value, flags=re.I | re.S)


def _safe_css(raw: Any) -> str:
    value = re.sub(r"@import\s+[^;]+;?", "", str(raw or ""), flags=re.I)
    return re.sub(r"url\(\s*(['\"]?)(?:https?:)?//.*?\1\s*\)", "none", value, flags=re.I | re.S)


def _shots(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        shot
        for group in snapshot.get("scene_groups") or []
        if isinstance(group, dict)
        for shot in group.get("shots") or []
        if isinstance(shot, dict) and str(shot.get("id") or "").strip()
    ]


def _entry_path(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    return str(
        value.get("path")
        or value.get("asset_path")
        or value.get("local_path")
        or value.get("audio_path")
        or value.get("video_path")
        or value.get("url")
        or value.get("asset_url")
        or ""
    )


def _local_path(value: Any, data_dir: str) -> str:
    raw = _entry_path(value).strip()
    if raw.startswith("/data/"):
        raw = os.path.join(data_dir, raw[len("/data/") :])
    elif raw.startswith("file://"):
        raw = raw[len("file://") :]
    if not raw or raw.startswith(("http://", "https://", "cos://")):
        return ""
    path = os.path.abspath(os.path.expanduser(raw))
    return path if os.path.isfile(path) else ""


def _selected_broll(shot: Dict[str, Any], selected: Dict[str, Any], data_dir: str) -> str:
    shot_id = str(shot.get("id") or "")
    selected_id = str(selected.get(shot_id) or "")
    options = [item for item in shot.get("broll_options") or [] if isinstance(item, dict)]
    ordered = sorted(options, key=lambda item: str(item.get("id") or "") != selected_id) if selected_id else options
    for option in ordered:
        path = _local_path(option, data_dir)
        if path:
            return path
    return ""


def _chrome_binary() -> str:
    configured = os.getenv("SMART_SLIDES_CHROME_BIN", "").strip()
    candidates = [
        configured,
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        shutil.which("google-chrome") or "",
        shutil.which("chromium") or "",
        shutil.which("chromium-browser") or "",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError("local Chrome is required to rasterize Podcastor HTML/MG overlays; set SMART_SLIDES_CHROME_BIN")


def _node_binary() -> str:
    configured = os.getenv("SMART_SLIDES_NODE_BIN", "").strip()
    candidates = [configured, shutil.which("node", path=_render_env().get("PATH")) or ""]
    for candidate in candidates:
        if not candidate or not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
            continue
        version = subprocess.run([candidate, "--version"], capture_output=True, text=True, check=False, env=_render_env())
        try:
            major = int(version.stdout.strip().lstrip("v").split(".", 1)[0])
        except (TypeError, ValueError):
            major = 0
        if version.returncode == 0 and major >= 22:
            return candidate
    raise RuntimeError("Node.js 22 or newer is required for local Chrome capture; set SMART_SLIDES_NODE_BIN")


def ensure_renderer_available(*, require_browser: bool = False) -> None:
    for binary in ("ffmpeg", "ffprobe"):
        if not _binary(binary):
            raise RuntimeError(f"{binary} is required for local rendering")
    if require_browser:
        _chrome_binary()
        _node_binary()


def _shot_design(snapshot: Dict[str, Any], shot: Dict[str, Any]) -> Dict[str, Any]:
    editor = snapshot.get("editor_state") if isinstance(snapshot.get("editor_state"), dict) else {}
    overrides = editor.get("html_design_overrides") if isinstance(editor.get("html_design_overrides"), dict) else {}
    override = overrides.get(str(shot.get("id") or "")) if isinstance(overrides.get(str(shot.get("id") or "")), dict) else {}
    spec = override.get("scene_design_spec") if isinstance(override.get("scene_design_spec"), dict) else {}
    base = shot.get("html_design") if isinstance(shot.get("html_design"), dict) else {}
    return {
        **base,
        **spec,
        "custom_html": _safe_html(spec.get("custom_html") if "custom_html" in spec else base.get("custom_html")),
        "custom_css": _safe_css(spec.get("custom_css") if "custom_css" in spec else base.get("custom_css")),
    }


def _shot_uses_html(shot: Dict[str, Any]) -> bool:
    director = shot.get("mg_director") if isinstance(shot.get("mg_director"), dict) else {}
    layer = shot.get("information_layer") if isinstance(shot.get("information_layer"), dict) else {}
    return bool(director.get("enabled")) or bool(layer.get("enabled")) or str(shot.get("scene_role") or "") == "broll_backdrop_overlay"


def _shot_mg_clip_offset_seconds(shot: Dict[str, Any]) -> float:
    try:
        return max(0.0, float(shot.get("mg_clip_offset_seconds") or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _write_overlay_page(
    snapshot: Dict[str, Any],
    shot: Dict[str, Any],
    work_dir: Path,
    *,
    freeze_animations: bool,
) -> Path:
    shot_id = str(shot.get("id") or "")
    overlays = work_dir / "overlays"
    overlays.mkdir(parents=True, exist_ok=True)
    page_path = overlays / f"{shot_id}.html"
    isolated = deepcopy(shot)
    isolated["html_design"] = _shot_design(snapshot, shot)
    editor = snapshot.get("editor_state") if isinstance(snapshot.get("editor_state"), dict) else {}
    isolated_project = {
        "topic": str(snapshot.get("topic") or shot.get("title") or "Smart Slides"),
        "production_format": "broll_html",
        "scene_groups": [{"title": str(shot.get("title") or shot_id), "shots": [isolated]}],
        "editor_state": {
            "avatar_enabled": False,
            "bgm_enabled": False,
            "shot_scripts": editor.get("shot_scripts") if isinstance(editor.get("shot_scripts"), dict) else {},
            "selected_broll_by_shot": {},
            "html_design_overrides": {},
            "mg_design_doc_overrides": editor.get("mg_design_doc_overrides") if isinstance(editor.get("mg_design_doc_overrides"), dict) else {},
        },
    }
    document = video_studio_planner.build_composition_preview_html(isolated_project)
    freeze_css = "*,*::before,*::after{animation:none!important;transition:none!important}" if freeze_animations else ""
    overlay_css = f"""
<style>
html,body{{margin:0!important;width:1920px!important;height:1080px!important;overflow:hidden!important;background:transparent!important}}
.shell{{display:block!important;width:1920px!important;height:1080px!important;background:transparent!important}}
.shell>header,.shell>footer,.controls,.media,.grade,.caption,.avatar{{display:none!important}}
.stage{{display:block!important;width:1920px!important;height:1080px!important;padding:0!important}}
.player{{width:1920px!important;height:1080px!important;max-width:none!important;border:0!important;border-radius:0!important;box-shadow:none!important;background:transparent!important;overflow:hidden!important}}
.scene{{display:block!important;opacity:1!important;pointer-events:none!important;transition:none!important}}
.info-layer{{opacity:1!important}}
{freeze_css}
</style>
"""
    page_path.write_text(document.replace("</head>", f"{overlay_css}</head>"), encoding="utf-8")
    return page_path


def capture_html_keyframe(page_path: str | Path, at_seconds: float, output_path: str | Path) -> str:
    """Capture a deterministic PNG from a local Podcastor HTML/MG page."""
    ensure_renderer_available(require_browser=True)
    return _capture_html_keyframe(
        page_path,
        at_seconds,
        output_path,
        chrome_binary=_chrome_binary(),
        width=_WIDTH,
        height=_HEIGHT,
        env=_render_env(),
    )


def _render_overlay_webm(
    snapshot: Dict[str, Any],
    shot: Dict[str, Any],
    work_dir: Path,
    duration: float,
) -> str:
    if not _shot_uses_html(shot):
        return ""
    if os.getenv("SMART_SLIDES_SKIP_BROWSER_RASTERIZER", "").lower() in {"1", "true", "yes"}:
        return ""
    page_path = _write_overlay_page(snapshot, shot, work_dir, freeze_animations=False)
    output_path = page_path.with_suffix(".webm")
    return render_alpha_webm(
        page_path,
        duration,
        output_path,
        start_at_seconds=_shot_mg_clip_offset_seconds(shot),
        frame_rate=_FRAME_RATE,
        chrome_binary=_chrome_binary(),
        ffmpeg_binary=_binary("ffmpeg") or "ffmpeg",
        width=_WIDTH,
        height=_HEIGHT,
        env=_render_env(),
    )


def _render_overlay_png(snapshot: Dict[str, Any], shot: Dict[str, Any], work_dir: Path) -> str:
    """Render the explicit diagnostic poster fallback."""
    if not _shot_uses_html(shot):
        return ""
    if os.getenv("SMART_SLIDES_SKIP_BROWSER_RASTERIZER", "").lower() in {"1", "true", "yes"}:
        return ""

    shot_id = str(shot.get("id") or "")
    page_path = _write_overlay_page(snapshot, shot, work_dir, freeze_animations=True)
    output_path = page_path.with_suffix(".png")
    profile_dir = page_path.parent / f"chrome-{shot_id}"
    command = [
        _chrome_binary(),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--force-color-profile=srgb",
        "--default-background-color=00000000",
        "--run-all-compositor-stages-before-draw",
        "--window-size=1920,1080",
        f"--user-data-dir={profile_dir}",
        f"--screenshot={output_path}",
        page_path.as_uri(),
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_render_env(),
        start_new_session=True,
    )
    deadline = time.monotonic() + 20
    while process.poll() is None and time.monotonic() < deadline:
        if output_path.is_file() and output_path.stat().st_size > 0:
            os.killpg(process.pid, signal.SIGTERM)
            process.communicate(timeout=5)
            return str(output_path)
        time.sleep(0.1)
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
    stdout, stderr = process.communicate(timeout=5)
    if process.returncode != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"could not rasterize original Podcastor HTML/MG for {shot_id}: {stderr.strip()}")
    return str(output_path)


def _render_overlay(snapshot: Dict[str, Any], shot: Dict[str, Any], work_dir: Path, duration: float) -> str:
    mode = os.getenv("SMART_SLIDES_HTML_RENDER_MODE", "animated").strip().lower() or "animated"
    if mode == "poster":
        return _render_overlay_png(snapshot, shot, work_dir)
    if mode != "animated":
        raise RuntimeError("SMART_SLIDES_HTML_RENDER_MODE must be 'animated' or 'poster'")
    return _render_overlay_webm(snapshot, shot, work_dir, duration)


def _is_image(path: str) -> bool:
    return Path(path).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _render_scene(visual_path: str, overlay_path: str, duration: float, output_path: Path) -> None:
    duration = max(0.1, float(duration))
    command: List[str] = ["ffmpeg", "-y", "-v", "error"]
    if _is_image(visual_path):
        command.extend(["-loop", "1", "-framerate", str(_FRAME_RATE), "-i", visual_path])
    else:
        command.extend(["-i", visual_path])
    # A short source may hold its final frame, but it must never restart and
    # replay within the same shot. Candidate selection normally prevents this.
    base_filter = (
        f"fps={_FRAME_RATE},scale={_WIDTH}:{_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={_WIDTH}:{_HEIGHT},setsar=1,tpad=stop_mode=clone:stop_duration={duration:.3f}"
    )
    if overlay_path:
        if _is_image(overlay_path):
            command.extend(["-loop", "1", "-framerate", str(_FRAME_RATE), "-i", overlay_path])
        else:
            command.extend(["-c:v", "libvpx-vp9", "-i", overlay_path])
        fade_out = max(0.0, duration - 0.45)
        filter_complex = (
            f"[0:v]{base_filter}[base];"
            f"[1:v]format=rgba,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.55:alpha=1,fade=t=out:st={fade_out:.3f}:d=0.45:alpha=1[mg];"
            "[base][mg]overlay=0:0:format=auto,format=yuv420p[v]"
        )
        command.extend(["-filter_complex", filter_complex, "-map", "[v]"])
    else:
        command.extend(["-vf", base_filter])
    command.extend(["-t", f"{duration:.3f}", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path)])
    subprocess.run(command, check=True, env=_render_env())


def _render_audio(source: str, duration: float, output_path: Path) -> None:
    safe_duration = max(0.1, float(duration))
    audio_filter = (
        "aformat=sample_rates=48000:channel_layouts=stereo,"
        f"atrim=0:{safe_duration:.3f}"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", source, "-af", audio_filter, "-c:a", "aac", "-b:a", "192k", str(output_path)],
        check=True,
        env=_render_env(),
    )


def _concat_input_file(paths: Iterable[Path], destination: Path) -> Path:
    """Write an FFmpeg concat-demuxer input without copying its media."""
    list_path = destination.with_suffix(".txt")
    lines = ["file '" + str(path).replace("'", "'\\''") + "'" for path in paths]
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return list_path


def _concat_file(paths: Iterable[Path], destination: Path) -> Path:
    list_path = _concat_input_file(paths, destination)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(destination)], check=True, env=_render_env())
    return destination


def _timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds_value, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds_value:02d},{milliseconds:03d}"


def _write_captions(shots: List[Dict[str, Any]], durations: List[float], scripts: Dict[str, Any], output: Path) -> None:
    entries: List[str] = []
    cursor = 0.0
    cue_index = 1
    for shot, duration in zip(shots, durations):
        shot_id = str(shot.get("id") or "")
        text = str(scripts.get(shot_id) or shot.get("narration") or shot.get("voiceover") or shot.get("title") or "").strip()
        for cue in video_studio_captions.build_caption_cues(text, duration):
            entries.extend(
                [
                    str(cue_index),
                    f"{_timestamp(cursor + cue['start_seconds'])} --> {_timestamp(cursor + cue['end_seconds'])}",
                    str(cue["text"]),
                    "",
                ]
            )
            cue_index += 1
        cursor += duration
    output.write_text("\n".join(entries), encoding="utf-8")


def _mix_bgm(narration: Path, bgm: str, volume: float, duration: float, output: Path) -> None:
    if not bgm:
        shutil.copy2(narration, output)
        return
    command = [
        "ffmpeg", "-y", "-v", "error", "-i", str(narration), "-stream_loop", "-1", "-i", bgm,
        "-filter_complex",
        f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo[voice];[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={max(0.0, min(0.8, volume)):.3f}[bgm];[voice][bgm]amix=inputs=2:duration=first:normalize=0[mix]",
        "-map", "[mix]", "-t", f"{duration:.3f}", "-c:a", "aac", "-b:a", "192k", str(output),
    ]
    subprocess.run(command, check=True, env=_render_env())


def _caption_filter(path: Path) -> str:
    escaped = str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    # libass interprets SRT styles on a 384x288 virtual canvas. These values
    # resolve to roughly 68px type, 145px side margins, and a 71px bottom
    # margin after original_size maps that canvas onto the 1920x1080 render.
    style = (
        "FontName=PingFang SC,FontSize=18,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H80000000,BorderStyle=1,Outline=1,Shadow=0,"
        "Alignment=2,MarginL=29,MarginR=29,MarginV=19,WrapStyle=2"
    )
    return f"subtitles=filename='{escaped}':original_size=1920x1080:force_style='{style}'"


def _media_duration_seconds(path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=_render_env(),
    )
    try:
        return max(0.0, float(result.stdout.strip()))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"could not read audio duration: {path}") from exc


def _require_voice_coverage(audio_path: str, duration: float, shot_id: str) -> None:
    actual = _media_duration_seconds(audio_path)
    if actual + 0.05 < duration:
        raise RuntimeError(
            f"Jogg voice for {shot_id} is {actual:.2f}s but the timeline is {duration:.2f}s; "
            "sync the project to measured Jogg voice timing before local render instead of padding silence"
        )


def render_snapshot(snapshot: Dict[str, Any], work_dir: str, data_dir: str, output_path: str) -> Dict[str, Any]:
    shots = _shots(snapshot)
    if not shots:
        raise RuntimeError("render snapshot has no shots")
    editor = snapshot.get("editor_state") if isinstance(snapshot.get("editor_state"), dict) else {}
    voice_assets = editor.get("voice_assets_by_shot") if isinstance(editor.get("voice_assets_by_shot"), dict) else {}
    avatar_assets = editor.get("avatar_assets_by_shot") if isinstance(editor.get("avatar_assets_by_shot"), dict) else {}
    selected_broll = editor.get("selected_broll_by_shot") if isinstance(editor.get("selected_broll_by_shot"), dict) else {}
    scripts = editor.get("shot_scripts") if isinstance(editor.get("shot_scripts"), dict) else {}
    durations = [max(0.1, float(shot.get("duration_seconds") or 1)) for shot in shots]
    require_browser = any(_shot_uses_html(shot) for shot in shots) and os.getenv("SMART_SLIDES_SKIP_BROWSER_RASTERIZER", "").lower() not in {"1", "true", "yes"}
    ensure_renderer_available(require_browser=require_browser)

    directory = Path(work_dir)
    directory.mkdir(parents=True, exist_ok=True)
    scenes_dir = directory / "scenes"
    scenes_dir.mkdir(exist_ok=True)
    audio_dir = directory / "audio"
    audio_dir.mkdir(exist_ok=True)
    scene_videos: List[Path] = []
    scene_audios: List[Path] = []
    manifest_shots: List[Dict[str, Any]] = []

    for index, (shot, duration) in enumerate(zip(shots, durations)):
        shot_id = str(shot.get("id") or "")
        audio_path = _local_path(voice_assets.get(shot_id), data_dir)
        if not audio_path:
            raise RuntimeError(f"missing Jogg voice audio for shot: {shot_id}")
        _require_voice_coverage(audio_path, duration, shot_id)
        avatar_path = _local_path(avatar_assets.get(shot_id), data_dir)
        broll_path = _selected_broll(shot, selected_broll, data_dir)
        visual_path = avatar_path or broll_path
        if not visual_path:
            raise RuntimeError(f"missing local visual asset for shot: {shot_id}")
        overlay_path = _render_overlay(snapshot, shot, directory, duration)
        scene_video = scenes_dir / f"{index:03d}-{shot_id}.mp4"
        scene_audio = audio_dir / f"{index:03d}-{shot_id}.m4a"
        _render_scene(visual_path, overlay_path, duration, scene_video)
        _render_audio(audio_path, duration, scene_audio)
        scene_videos.append(scene_video)
        scene_audios.append(scene_audio)
        manifest_shots.append(
            {
                "shot_id": shot_id,
                "duration": round(duration, 3),
                "avatar_visual": bool(avatar_path),
                "visual_path": visual_path,
                "overlay_path": overlay_path,
                "mg_clip_offset_seconds": _shot_mg_clip_offset_seconds(shot),
            }
        )

    # Do not duplicate the full video timeline into a temporary visuals.mp4.
    # The final composition can consume the scene list directly.
    visual_list = _concat_input_file(scene_videos, directory / "visuals")
    narration = _concat_file(scene_audios, directory / "narration.m4a")
    captions = directory / "captions.srt"
    _write_captions(shots, durations, scripts, captions)
    bgm = _local_path(editor.get("selected_bgm_track"), data_dir) if bool(editor.get("bgm_enabled", True)) else ""
    mixed_audio = directory / "mixed.m4a"
    total_duration = sum(durations)
    _mix_bgm(narration, bgm, float(editor.get("bgm_volume") or 0.35), total_duration, mixed_audio)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(visual_list), "-i", str(mixed_audio),
            "-vf", _caption_filter(captions), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(target),
        ],
        check=True,
        env=_render_env(),
    )
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError("local FFmpeg renderer did not produce an MP4")
    manifest = {
        "version": "smart_slides_local_ffmpeg_render_v1",
        "backend": "local_ffmpeg",
        "duration_seconds": round(total_duration, 3),
        "shots": manifest_shots,
        "narration": str(narration),
        "captions": str(captions),
    }
    (directory / "render-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def render_work(work: Dict[str, Any], store: Any, data_dir: str) -> Dict[str, Any]:
    work_id = str(work.get("id") or "")
    project_id = str(work.get("project_id") or "")
    work_dir = Path(data_dir) / "video_studio_renders" / work_id
    output_path = Path(data_dir) / "video_studio_outputs" / project_id / f"{work_id}.mp4"
    try:
        store.update_work(work_id, {"status": "rendering", "progress": {"phase": "ffmpeg_composition", "percent": 10}, "error": ""}, log_message="开始依据 Podcastor 编辑器快照进行本地 FFmpeg 合成。")
        manifest = render_snapshot(work.get("render_snapshot") or {}, str(work_dir), data_dir, str(output_path))
        output = {"url": f"/data/video_studio_outputs/{project_id}/{work_id}.mp4", "path": str(output_path), "duration_seconds": manifest["duration_seconds"], "backend": "local_ffmpeg"}
        project_update_error: Optional[Exception] = None
        try:
            _update_project_output(project_id, work_id, output, data_dir)
        except Exception as exc:
            project_update_error = exc
        return store.update_work(
            work_id,
            {"status": "success", "output": output, "progress": {"phase": "completed", "percent": 100}, "error": ""},
            log_level="warning" if project_update_error else "info",
            log_message=f"MP4 已完成，但项目输出索引更新失败：{project_update_error}" if project_update_error else "本地 FFmpeg MP4 渲染完成。",
        )
    except Exception as exc:
        return store.update_work(work_id, {"status": "failed", "progress": {"phase": "failed", "percent": 100}, "error": str(exc)}, log_level="error", log_message=f"本地 FFmpeg 渲染失败：{exc}")


def _update_project_output(project_id: str, work_id: str, output: Dict[str, Any], data_dir: str) -> None:
    from backend.services.video_studio_store import VideoStudioStore

    project_store = VideoStudioStore(data_dir)
    project = project_store.get_project(project_id)
    if not project:
        return
    render_layer = project.get("render_layer") if isinstance(project.get("render_layer"), dict) else {}
    jobs = render_layer.get("jobs") if isinstance(render_layer.get("jobs"), list) else []
    job = {"work_id": work_id, "status": "success", "output": output}
    render_layer = {**render_layer, "jobs": [job, *[item for item in jobs if isinstance(item, dict) and str(item.get("work_id") or "") != work_id]], "latest_output": output}
    project_store.update_project(project_id, {"final_video_url": str(output.get("url") or ""), "render_layer": render_layer})


def start_render_async(work: Dict[str, Any], store: Any, data_dir: str) -> None:
    work_id = str(work.get("id") or "")
    if not work_id:
        raise ValueError("work id is required")
    with _ACTIVE_LOCK:
        if work_id in _ACTIVE_WORKS or str(work.get("status") or "") == "success":
            return
        _ACTIVE_WORKS.add(work_id)

    def runner() -> None:
        try:
            render_work(work, store, data_dir)
        finally:
            with _ACTIVE_LOCK:
                _ACTIVE_WORKS.discard(work_id)

    threading.Thread(target=runner, name=f"smart-slides-ffmpeg-{work_id}", daemon=True).start()
