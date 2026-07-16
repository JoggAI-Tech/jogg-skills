from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


HYPERFRAMES_VERSION = "0.7.59"
_ACTIVE_WORKS: set[str] = set()
_ACTIVE_LOCK = threading.RLock()


def _hyperframes_prefix() -> List[str]:
    configured = os.getenv("SMART_SLIDES_HYPERFRAMES_BIN", "").strip()
    if configured:
        executable = os.path.abspath(os.path.expanduser(configured))
        if not os.path.isfile(executable) or not os.access(executable, os.X_OK):
            raise RuntimeError(f"SMART_SLIDES_HYPERFRAMES_BIN is not executable: {executable}")
        return [executable]
    executable = shutil.which("hyperframes")
    if executable:
        return [executable]
    npx = shutil.which("npx")
    if npx:
        return [npx, "--no-install", f"hyperframes@{HYPERFRAMES_VERSION}"]
    raise RuntimeError("HyperFrames 0.7.59 is not installed locally")


def _render_env() -> Dict[str, str]:
    env = dict(os.environ)
    tool_dir = os.path.abspath(os.path.expanduser(env.get("SMART_SLIDES_TOOL_DIR", "~/.codex/smart-slides/bin")))
    if os.path.isfile(os.path.join(tool_dir, "ffprobe")):
        env["PATH"] = f"{tool_dir}{os.pathsep}{env.get('PATH', '')}"
    return env


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


def _safe_html(raw: Any) -> str:
    value = str(raw or "")
    value = re.sub(r"<\s*(script|iframe|object|embed)\b[^>]*>.*?<\s*/\s*\1\s*>", "", value, flags=re.I | re.S)
    value = re.sub(r"<\s*/?\s*(script|iframe|object|embed)\b[^>]*>", "", value, flags=re.I | re.S)
    value = re.sub(r"\s(?:src|srcset|href|xlink:href)\s*=\s*(['\"])(?:https?:)?//.*?\1", "", value, flags=re.I | re.S)
    value = re.sub(r"\s(?:src|srcset|href|xlink:href)\s*=\s*(?:https?:)?//[^\s>]+", "", value, flags=re.I)
    value = re.sub(r"\son\w+\s*=\s*(['\"]).*?\1", "", value, flags=re.I | re.S)
    value = re.sub(r"\son\w+\s*=\s*[^\s>]+", "", value, flags=re.I)
    value = re.sub(r"url\(\s*(['\"]?)(?:https?:)?//.*?\1\s*\)", "none", value, flags=re.I | re.S)
    return value


def _safe_css(raw: Any) -> str:
    value = re.sub(r"@import\s+[^;]+;?", "", str(raw or ""), flags=re.I)
    return re.sub(r"url\(\s*(['\"]?)(?:https?:)?//.*?\1\s*\)", "none", value, flags=re.I | re.S)


def _copy_asset(source: str, assets_dir: Path, name: str) -> str:
    suffix = Path(source).suffix.lower() or ".bin"
    destination = assets_dir / f"{name}{suffix}"
    shutil.copy2(source, destination)
    return destination.relative_to(assets_dir.parent).as_posix()


def _build_narration(audio_paths: List[str], durations: List[float], output: Path) -> None:
    if not audio_paths:
        raise RuntimeError("render snapshot has no Jogg voice assets")
    command: List[str] = ["ffmpeg", "-y", "-v", "error"]
    for path in audio_paths:
        command.extend(["-i", path])
    filters: List[str] = []
    labels: List[str] = []
    for index, duration in enumerate(durations):
        safe_duration = max(0.1, float(duration))
        label = f"a{index}"
        filters.append(
            f"[{index}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
            f"atrim=0:{safe_duration:.3f},apad=pad_dur={safe_duration:.3f},"
            f"atrim=0:{safe_duration:.3f}[{label}]"
        )
        labels.append(f"[{label}]")
    filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1[narration]")
    command.extend(["-filter_complex", ";".join(filters), "-map", "[narration]", "-c:a", "aac", "-b:a", "192k", str(output)])
    subprocess.run(command, check=True)


def _fallback_transcript(shots: List[Dict[str, Any]], durations: List[float], scripts: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    words: List[Dict[str, Any]] = []
    cursor = 0.0
    word_id = 0
    scripts = scripts or {}
    for shot, duration in zip(shots, durations):
        shot_id = str(shot.get("id") or "")
        narration = str(scripts.get(shot_id) or shot.get("narration") or shot.get("voiceover") or shot.get("title") or "").strip()
        tokens = [token for token in re.split(r"(?<=[，。！？；,.!?;])|\s+", narration) if token.strip()]
        if not tokens:
            cursor += duration
            continue
        unit = max(0.18, duration / len(tokens))
        for index, token in enumerate(tokens):
            start = cursor + index * unit
            end = cursor + min(duration, (index + 1) * unit)
            words.append({"id": f"w{word_id}", "text": token.strip(), "start": round(start, 3), "end": round(end, 3)})
            word_id += 1
        cursor += duration
    return words


def _transcribe(work_dir: Path, narration: Path, fallback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    transcript_path = work_dir / "transcript.json"
    if os.getenv("SMART_SLIDES_SKIP_TRANSCRIPTION", "").lower() not in {"1", "true", "yes"}:
        command = [
            *_hyperframes_prefix(), "transcribe", str(narration),
            "--dir", str(work_dir), "--engine", "whisper", "--language", "zh", "--optional", "--json",
        ]
        subprocess.run(command, cwd=work_dir, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if transcript_path.is_file():
        try:
            payload = json.loads(transcript_path.read_text(encoding="utf-8"))
            if isinstance(payload, list) and payload:
                return [item for item in payload if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            pass
    transcript_path.write_text(json.dumps(fallback, ensure_ascii=False, indent=2), encoding="utf-8")
    return fallback


def _caption_cues(words: Iterable[Dict[str, Any]], max_chars: int = 24) -> List[Dict[str, Any]]:
    cues: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for word in words:
        text = str(word.get("text") or "").strip()
        if not text:
            continue
        start = max(0.0, float(word.get("start") or 0))
        end = max(start + 0.05, float(word.get("end") or start + 0.2))
        joined = f"{current['text']}{text}" if current else text
        if current and len(joined) <= max_chars and start - float(current["end"]) <= 0.65:
            current["text"] = joined
            current["end"] = end
        else:
            if current:
                cues.append(current)
            current = {"text": text, "start": start, "end": end}
        if text.endswith(("。", "！", "？", ".", "!", "?")) and current:
            cues.append(current)
            current = None
    if current:
        cues.append(current)
    return cues


def build_composition(snapshot: Dict[str, Any], work_dir: str, data_dir: str) -> Dict[str, Any]:
    directory = Path(work_dir)
    assets_dir = directory / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    shots = _shots(snapshot)
    if not shots:
        raise RuntimeError("render snapshot has no shots")

    editor = snapshot.get("editor_state") if isinstance(snapshot.get("editor_state"), dict) else {}
    voice_assets = editor.get("voice_assets_by_shot") if isinstance(editor.get("voice_assets_by_shot"), dict) else {}
    avatar_assets = editor.get("avatar_assets_by_shot") if isinstance(editor.get("avatar_assets_by_shot"), dict) else {}
    selected_broll = editor.get("selected_broll_by_shot") if isinstance(editor.get("selected_broll_by_shot"), dict) else {}
    html_overrides = editor.get("html_design_overrides") if isinstance(editor.get("html_design_overrides"), dict) else {}
    scripts = editor.get("shot_scripts") if isinstance(editor.get("shot_scripts"), dict) else {}

    durations = [max(0.1, float(shot.get("duration_seconds") or 1)) for shot in shots]
    audio_sources = [_local_path(voice_assets.get(str(shot.get("id") or "")), data_dir) for shot in shots]
    missing_audio = [str(shot.get("id") or "") for shot, path in zip(shots, audio_sources) if not path]
    if missing_audio:
        raise RuntimeError(f"missing Jogg voice audio for shots: {', '.join(missing_audio)}")

    narration = directory / "narration.m4a"
    _build_narration(audio_sources, durations, narration)
    transcript = _transcribe(directory, narration, _fallback_transcript(shots, durations, scripts))
    shutil.copy2(Path(__file__).resolve().parent / "vendor" / "gsap.min.js", directory / "gsap.min.js")
    plugin_assets = Path(__file__).resolve().parents[2] / "assets" / "fonts"
    font_sources = {
        "zen-maru-bold.ttf": plugin_assets / "zen-maru-gothic" / "ZenMaruGothic-Bold.ttf",
    }
    for filename, source in font_sources.items():
        shutil.copy2(source, assets_dir / filename)

    media_markup: List[str] = []
    overlay_markup: List[str] = []
    animation_markup: List[str] = []
    shot_manifest: List[Dict[str, Any]] = []
    cursor = 0.0
    transition = 0.35
    for index, (shot, duration) in enumerate(zip(shots, durations)):
        shot_id = str(shot.get("id") or "")
        avatar_path = _local_path(avatar_assets.get(shot_id), data_dir)
        broll_path = _selected_broll(shot, selected_broll, data_dir)
        visual_path = avatar_path or broll_path
        if not visual_path:
            raise RuntimeError(f"missing local visual asset for shot: {shot_id}")
        visual_name = _copy_asset(visual_path, assets_dir, f"shot-{index:03d}")
        visual_start = cursor
        visual_duration = duration
        initial_style = ' style="opacity:0"'
        is_image = Path(visual_path).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        if is_image:
            media_markup.append(
                f'<img id="visual-{index}" class="clip visual" data-start="{visual_start:.3f}" '
                f'data-duration="{visual_duration:.3f}" data-track-index="{index}" src="{html.escape(visual_name, quote=True)}" alt=""{initial_style} />'
            )
        else:
            media_markup.append(
                f'<video id="visual-{index}" class="clip visual" data-start="{visual_start:.3f}" '
                f'data-duration="{visual_duration:.3f}" data-track-index="{index}" src="{html.escape(visual_name, quote=True)}" muted playsinline preload="auto"{initial_style}></video>'
            )
        html_override = html_overrides.get(shot_id) if isinstance(html_overrides.get(shot_id), dict) else {}
        scene_spec = html_override.get("scene_design_spec") if isinstance(html_override.get("scene_design_spec"), dict) else {}
        base_html_design = shot.get("html_design") if isinstance(shot.get("html_design"), dict) else {}
        html_design = {**base_html_design, **scene_spec}
        custom_html = _safe_html(html_design.get("custom_html"))
        custom_css = _safe_css(html_design.get("custom_css"))
        title = html.escape(str(shot.get("title") or shot_id))
        overlay_markup.append(
            f'<section id="overlay-{index}" class="clip overlay" data-start="{cursor:.3f}" data-duration="{duration:.3f}" '
            f'data-track-index="{100 + index}"><style>{custom_css}</style><div class="shot-meta">{index + 1:02d}</div>'
            f'<div class="mg-content">{custom_html or f"<h2>{title}</h2>"}</div></section>'
        )
        if index:
            overlay_markup.append(
                f'<div id="transition-{index}" class="clip transition" data-start="{cursor:.3f}" '
                f'data-duration="{transition:.3f}" data-track-index="{250 + index}" data-layout-ignore></div>'
            )
        animation_markup.append(
            f'tl.fromTo("#visual-{index}", {{opacity:0}}, {{opacity:1,duration:{transition},ease:"power2.out"}}, {visual_start:.3f});'
            f'tl.from("#overlay-{index} .shot-meta", {{opacity:0,x:-32,duration:.45,ease:"expo.out"}}, {cursor + .12:.3f});'
            f'tl.from("#overlay-{index} .mg-content", {{opacity:0,y:34,duration:.55,ease:"power3.out"}}, {cursor + .2:.3f});'
            f'tl.from("#overlay-{index} .mg-content > *", {{opacity:0,y:20,duration:.45,stagger:.08,ease:"back.out(1.2)"}}, {cursor + .28:.3f});'
            + (f'tl.fromTo("#transition-{index}", {{xPercent:0}}, {{xPercent:105,duration:{transition},ease:"power2.inOut"}}, {cursor:.3f});' if index else "")
        )
        shot_manifest.append({"shot_id": shot_id, "start": round(cursor, 3), "duration": round(duration, 3), "avatar_visual": bool(avatar_path), "visual": visual_name})
        cursor += duration

    caption_markup = [
        f'<div id="caption-{index}" class="clip caption" data-start="{cue["start"]:.3f}" data-duration="{max(.1, cue["end"] - cue["start"] - .01):.3f}" '
        f'data-track-index="400">{html.escape(str(cue["text"]))}</div>'
        for index, cue in enumerate(_caption_cues(transcript))
    ]
    bgm_markup = ""
    if bool(editor.get("bgm_enabled", True)):
        bgm = editor.get("selected_bgm_track") if isinstance(editor.get("selected_bgm_track"), dict) else {}
        bgm_path = _local_path(bgm, data_dir)
        if bgm_path:
            bgm_name = _copy_asset(bgm_path, assets_dir, "bgm")
            volume = max(0.0, min(1.0, float(editor.get("bgm_volume") or 0.35)))
            bgm_markup = f'<audio id="bgm-audio" data-start="0" data-duration="{cursor:.3f}" data-track-index="300" src="{html.escape(bgm_name, quote=True)}" data-volume="{volume:.3f}" data-loop></audio>'

    animation_markup.append(f'tl.to("#visual-{len(shots) - 1}", {{opacity:0,duration:.45,ease:"power1.in"}}, {max(0.0, cursor - .45):.3f});')
    document = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=1920,height=1080">
<script src="./gsap.min.js"></script><style>
@font-face{{font-family:"Zen Maru Gothic";src:url("./assets/zen-maru-bold.ttf");font-weight:700}}
*{{box-sizing:border-box}}html,body{{margin:0;width:1920px;height:1080px;overflow:hidden;background:#050505}}
body{{font-family:"Zen Maru Gothic",sans-serif;color:#fff;letter-spacing:0}}
#root{{position:relative;width:1920px;height:1080px;overflow:hidden;background:#050505}}
.visual{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#111}}
.overlay{{position:absolute;inset:0;padding:72px 96px;display:flex;align-items:flex-start;justify-content:space-between}}
.shot-meta{{font:700 24px/1 "Zen Maru Gothic",sans-serif;background:#111;color:#fff;padding:12px 15px;border-left:6px solid #f2c94c}}
.mg-content{{max-width:1120px;margin-left:auto;text-shadow:0 2px 18px rgba(0,0,0,.7)}}
.mg-content h2{{margin:0;font:700 76px/1.08 "Zen Maru Gothic",sans-serif;max-width:1100px}}
.transition{{position:absolute;inset:0;background:#f2c94c}}
.caption{{position:absolute;left:240px;right:240px;bottom:62px;padding:16px 24px;background:rgba(0,0,0,.76);border-radius:6px;text-align:center;font-size:34px;line-height:1.35;font-weight:600;text-shadow:0 2px 8px #000}}
</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="{cursor:.3f}" data-width="1920" data-height="1080">
<div class="media-layer">{''.join(media_markup)}</div>{''.join(overlay_markup)}{''.join(caption_markup)}
<audio id="narration-audio" data-start="0" data-duration="{cursor:.3f}" data-track-index="350" src="./narration.m4a" data-volume="1"></audio>{bgm_markup}
</div><script>window.__timelines=window.__timelines||{{}};const tl=gsap.timeline({{paused:true}});{''.join(animation_markup)}window.__timelines["main"]=tl;</script></body></html>'''
    (directory / "index.html").write_text(document, encoding="utf-8")
    (directory / "hyperframes.json").write_text(json.dumps({"version": 1, "name": directory.name, "composition": "main"}, indent=2), encoding="utf-8")
    manifest = {"version": "smart_slides_local_render_v1", "duration_seconds": round(cursor, 3), "shots": shot_manifest, "narration": "narration.m4a", "transcript": "transcript.json"}
    (directory / "render-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _run_render_command(work_dir: Path, output_path: Path) -> None:
    override = os.getenv("SMART_SLIDES_RENDER_COMMAND", "").strip()
    if override:
        env = {**_render_env(), "SMART_SLIDES_COMPOSITION_DIR": str(work_dir), "SMART_SLIDES_OUTPUT": str(output_path)}
        subprocess.run(["/bin/sh", "-c", override], cwd=work_dir, env=env, check=True)
        return
    prefix = _hyperframes_prefix()
    env = _render_env()
    subprocess.run([*prefix, "lint", "."], cwd=work_dir, env=env, check=True)
    subprocess.run([*prefix, "check", ".", "--no-contrast"], cwd=work_dir, env=env, check=True)
    subprocess.run([*prefix, "render", "--output", str(output_path), "--quality", os.getenv("SMART_SLIDES_RENDER_QUALITY", "standard"), "--strict"], cwd=work_dir, env=env, check=True)


def render_work(work: Dict[str, Any], store: Any, data_dir: str) -> Dict[str, Any]:
    work_id = str(work.get("id") or "")
    project_id = str(work.get("project_id") or "")
    work_dir = Path(data_dir) / "video_studio_renders" / work_id
    output_path = Path(data_dir) / "video_studio_outputs" / project_id / f"{work_id}.mp4"
    work_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        store.update_work(work_id, {"status": "rendering", "progress": {"phase": "composition", "percent": 10}, "error": ""}, log_message="开始生成本地 HyperFrames composition。")
        manifest = build_composition(work.get("render_snapshot") or {}, str(work_dir), data_dir)
        store.update_work(work_id, {"progress": {"phase": "rendering", "percent": 35}}, log_message="本地 Chrome 和 FFmpeg 开始渲染。")
        _run_render_command(work_dir, output_path)
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise RuntimeError("local renderer did not produce an MP4")
        output = {"url": f"/data/video_studio_outputs/{project_id}/{work_id}.mp4", "path": str(output_path), "duration_seconds": manifest["duration_seconds"], "backend": "local_hyperframes_ffmpeg"}
        project_update_error: Optional[Exception] = None
        try:
            _update_project_output(project_id, work_id, output, data_dir)
        except Exception as exc:
            project_update_error = exc
        completed = store.update_work(
            work_id,
            {"status": "success", "output": output, "progress": {"phase": "completed", "percent": 100}, "error": ""},
            log_level="warning" if project_update_error else "info",
            log_message=f"MP4 已完成，但项目输出索引更新失败：{project_update_error}" if project_update_error else "本地 MP4 渲染完成。",
        )
        return completed
    except Exception as exc:
        return store.update_work(work_id, {"status": "failed", "progress": {"phase": "failed", "percent": 100}, "error": str(exc)}, log_level="error", log_message=f"本地渲染失败：{exc}")


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

    threading.Thread(target=runner, name=f"smart-slides-render-{work_id}", daemon=True).start()
