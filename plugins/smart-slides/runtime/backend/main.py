import os
from pathlib import Path


def _load_env_file(path: Path) -> None:
    """Load local runtime configuration without overriding process settings."""
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not key.replace("_", "a").isalnum() or not (key[0].isalpha() or key[0] == "_"):
            continue
        if value.startswith(('"', "'")) and value.endswith(value[:1]) and len(value) >= 2:
            value = value[1:-1]
        os.environ.setdefault(key, value)


_PLUGIN_ROOT = Path(__file__).resolve().parents[2]
_load_env_file(_PLUGIN_ROOT / ".env")
_load_env_file(Path.home() / ".codex" / "smart-slides" / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.video_studio import DATA_DIR, router


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


app = FastAPI(title="smart-slides local Video Studio")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1", "http://localhost"],
    allow_origin_regex=r"https?://(127\.0\.0\.1|localhost)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(DATA_DIR, exist_ok=True)
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "smart-slides"}


FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").is_file():
    app.mount("/", SPAStaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
