from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional

_WIDTH = 1920
_HEIGHT = 1080
_CAPTURE_HELPER = Path(__file__).with_name("chrome_capture.mjs")


def _frame_times_ms(duration: float, frame_rate: float, start_at_seconds: float = 0.0) -> list[float]:
    duration_ms = max(0.0, float(duration) * 1000.0)
    start_ms = max(0.0, float(start_at_seconds) * 1000.0)
    step_ms = 1000.0 / float(frame_rate)
    times = [index * step_ms for index in range(int(math.floor(duration_ms / step_ms)) + 1)]
    if not times or duration_ms - times[-1] > 0.0001:
        times.append(duration_ms)
    return [round(start_ms + min(duration_ms, value), 6) for value in times]


def _freeze_animation_expression(time_ms: float) -> str:
    return f"""
(async () => {{
  const __SMART_SLIDES_FRAME_TIME_MS__ = {float(time_ms):.6f};
  const documents = [document];
  for (const frame of document.querySelectorAll('iframe[srcdoc]')) {{
    try {{
      if (frame.contentDocument) documents.push(frame.contentDocument);
    }} catch (_) {{}}
  }}
  let animationCount = 0;
  for (const currentDocument of documents) {{
    if (currentDocument.fonts && currentDocument.fonts.ready) {{
      await currentDocument.fonts.ready;
    }}
    for (const animation of currentDocument.getAnimations({{subtree: true}})) {{
      try {{
        animation.pause();
        animation.currentTime = __SMART_SLIDES_FRAME_TIME_MS__;
        animationCount += 1;
      }} catch (_) {{}}
    }}
    if (currentDocument.documentElement) currentDocument.documentElement.getBoundingClientRect();
  }}
  return animationCount;
}})()
""".strip()


def _evaluate_at_time(session: Any, time_ms: float) -> None:
    expression = _freeze_animation_expression(time_ms)
    evaluate_all = getattr(session, "evaluate_all_contexts", None)
    if callable(evaluate_all):
        evaluate_all(expression)
    else:
        session.evaluate(expression)


def _session(
    *,
    chrome_binary: str,
    profile_dir: Path,
    width: int,
    height: int,
    env: Optional[Dict[str, str]],
    session_factory: Callable[..., Any],
) -> Any:
    return session_factory(
        chrome_binary=chrome_binary,
        profile_dir=profile_dir,
        width=width,
        height=height,
        env=env,
    )


def _node_binary(env: Optional[Dict[str, str]] = None) -> str:
    process_env = env or dict(os.environ)
    configured = process_env.get("SMART_SLIDES_NODE_BIN", "").strip()
    candidates = [
        configured,
        shutil.which("node", path=process_env.get("PATH")) or "",
        "/opt/homebrew/bin/node",
        "/usr/local/bin/node",
    ]
    for binary in candidates:
        if not binary or not os.path.isfile(binary) or not os.access(binary, os.X_OK):
            continue
        version = subprocess.run([binary, "--version"], capture_output=True, text=True, check=False, env=process_env)
        try:
            major = int(version.stdout.strip().lstrip("v").split(".", 1)[0])
        except (TypeError, ValueError):
            major = 0
        if version.returncode == 0 and major >= 22:
            return binary
    raise RuntimeError("Node.js 22 or newer is required for local Chrome capture")


def _capture_command(
    *,
    chrome_binary: str,
    profile_dir: Path,
    page: Path,
    width: int,
    height: int,
    env: Optional[Dict[str, str]],
) -> list[str]:
    return [
        _node_binary(env),
        str(_CAPTURE_HELPER),
        "--chrome",
        chrome_binary,
        "--profile",
        str(profile_dir),
        "--page",
        page.as_uri(),
        "--width",
        str(int(width)),
        "--height",
        str(int(height)),
    ]


def capture_html_keyframe(
    page_path: str | Path,
    at_seconds: float,
    output_path: str | Path,
    *,
    chrome_binary: Optional[str] = None,
    width: int = _WIDTH,
    height: int = _HEIGHT,
    env: Optional[Dict[str, str]] = None,
    session_factory: Optional[Callable[..., Any]] = None,
) -> str:
    page = Path(page_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    if not page.is_file():
        raise FileNotFoundError(f"local HTML page does not exist: {page}")
    if float(at_seconds) < 0:
        raise ValueError("keyframe timestamp must not be negative")
    binary = str(chrome_binary or os.getenv("SMART_SLIDES_CHROME_BIN", "")).strip()
    if not binary:
        raise RuntimeError("local Chrome binary is required for HTML keyframe capture")
    output.parent.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(tempfile.mkdtemp(prefix=f".chrome-{output.stem}-", dir=output.parent))
    browser = None
    try:
        if session_factory is not None:
            browser = _session(
                chrome_binary=binary,
                profile_dir=profile_dir,
                width=int(width),
                height=int(height),
                env=env,
                session_factory=session_factory,
            )
            browser.navigate(page.as_uri())
            _evaluate_at_time(browser, float(at_seconds) * 1000.0)
            png = browser.screenshot_png()
            if not png:
                raise RuntimeError(f"local Chrome returned an empty keyframe for {page}")
            output.write_bytes(png)
        else:
            command = [
                *_capture_command(
                    chrome_binary=binary,
                    profile_dir=profile_dir,
                    page=page,
                    width=int(width),
                    height=int(height),
                    env=env,
                ),
                "--at-ms",
                f"{float(at_seconds) * 1000.0:.6f}",
            ]
            with output.open("wb") as stream:
                captured = subprocess.run(command, stdout=stream, stderr=subprocess.PIPE, env=env, check=False)
            if captured.returncode != 0:
                detail = captured.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(f"local Chrome could not capture HTML keyframe: {detail}")
    finally:
        if browser is not None:
            browser.close()
        shutil.rmtree(profile_dir, ignore_errors=True)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"local Chrome did not produce a keyframe: {output}")
    return str(output)


def render_alpha_webm(
    page_path: str | Path,
    duration: float,
    output_path: str | Path,
    *,
    start_at_seconds: float = 0.0,
    frame_rate: float = 24,
    chrome_binary: Optional[str] = None,
    ffmpeg_binary: str = "ffmpeg",
    width: int = _WIDTH,
    height: int = _HEIGHT,
    env: Optional[Dict[str, str]] = None,
    session_factory: Optional[Callable[..., Any]] = None,
    process_factory: Callable[..., Any] = subprocess.Popen,
) -> str:
    page = Path(page_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    safe_duration = float(duration)
    safe_start_at = float(start_at_seconds)
    safe_frame_rate = float(frame_rate)
    if not page.is_file():
        raise FileNotFoundError(f"local HTML page does not exist: {page}")
    if not math.isfinite(safe_duration) or safe_duration <= 0:
        raise ValueError("alpha overlay duration must be positive")
    if not math.isfinite(safe_start_at) or safe_start_at < 0:
        raise ValueError("alpha overlay start time must not be negative")
    if not math.isfinite(safe_frame_rate) or safe_frame_rate <= 0:
        raise ValueError("alpha overlay frame rate must be positive")
    binary = str(chrome_binary or os.getenv("SMART_SLIDES_CHROME_BIN", "")).strip()
    if not binary:
        raise RuntimeError("local Chrome binary is required for animated HTML rendering")
    output.parent.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(tempfile.mkdtemp(prefix=f".chrome-{output.stem}-", dir=output.parent))
    command = [
        ffmpeg_binary,
        "-y",
        "-v",
        "error",
        "-f",
        "image2pipe",
        "-framerate",
        f"{safe_frame_rate:g}",
        "-vcodec",
        "png",
        "-i",
        "pipe:0",
        "-t",
        f"{safe_duration:.6f}",
        "-c:v",
        "libvpx-vp9",
        "-deadline",
        "good",
        "-cpu-used",
        "4",
        "-row-mt",
        "1",
        "-crf",
        "18",
        "-b:v",
        "0",
        "-pix_fmt",
        "yuva420p",
        "-auto-alt-ref",
        "0",
        "-metadata:s:v:0",
        "alpha_mode=1",
        "-an",
        str(output),
    ]
    process = process_factory(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=env,
    )
    browser = None
    capture = None
    try:
        if process.stdin is None:
            raise RuntimeError("could not open FFmpeg image pipe")
        if session_factory is not None:
            browser = _session(
                chrome_binary=binary,
                profile_dir=profile_dir,
                width=int(width),
                height=int(height),
                env=env,
                session_factory=session_factory,
            )
            browser.navigate(page.as_uri())
            for time_ms in _frame_times_ms(safe_duration, safe_frame_rate, safe_start_at):
                _evaluate_at_time(browser, time_ms)
                png = browser.screenshot_png()
                if not png:
                    raise RuntimeError(f"local Chrome returned an empty animation frame at {time_ms:.3f}ms")
                process.stdin.write(png)
            process.stdin.close()
        else:
            capture_command = [
                *_capture_command(
                    chrome_binary=binary,
                    profile_dir=profile_dir,
                    page=page,
                    width=int(width),
                    height=int(height),
                    env=env,
                ),
                "--duration",
                f"{safe_duration:.6f}",
                "--frame-rate",
                f"{safe_frame_rate:g}",
                "--start-ms",
                f"{safe_start_at * 1000.0:.6f}",
            ]
            capture = subprocess.Popen(
                capture_command,
                stdin=subprocess.DEVNULL,
                stdout=process.stdin,
                stderr=subprocess.PIPE,
                env=env,
                start_new_session=True,
            )
            process.stdin.close()
            _, capture_stderr = capture.communicate(timeout=max(30.0, safe_duration * 4.0))
            if capture.stderr is not None:
                capture.stderr.close()
            if capture.returncode != 0:
                detail = capture_stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(f"local Chrome could not rasterize animated HTML: {detail}")
        return_code = process.wait(timeout=max(30.0, safe_duration * 4.0))
        stderr = process.stderr.read() if process.stderr is not None else b""
        if process.stderr is not None:
            process.stderr.close()
        if return_code != 0:
            detail = stderr.decode("utf-8", errors="replace").strip() if isinstance(stderr, bytes) else str(stderr).strip()
            raise RuntimeError(f"FFmpeg could not encode animated HTML alpha video: {detail}")
    except Exception:
        if capture is not None and capture.poll() is None:
            try:
                os.killpg(capture.pid, 15)
                capture.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(capture.pid, 9)
                except ProcessLookupError:
                    pass
                capture.wait(timeout=5)
        if getattr(process, "stdin", None) is not None and not process.stdin.closed:
            process.stdin.close()
        if getattr(process, "returncode", None) is None:
            process.kill()
            process.wait(timeout=5)
        raise
    finally:
        if browser is not None:
            browser.close()
        shutil.rmtree(profile_dir, ignore_errors=True)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"FFmpeg did not produce an animated alpha overlay: {output}")
    return str(output)
