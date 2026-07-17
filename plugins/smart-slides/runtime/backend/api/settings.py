"""Loopback-only setup API for Smart Slides local credentials."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

_MANAGED_KEYS = ("JOGG_API_KEY", "PEXELS_API_KEY")


class SettingsPatch(BaseModel):
    jogg_api_key: Optional[str] = Field(default=None, max_length=512)
    pexels_api_key: Optional[str] = Field(default=None, max_length=512)
    clear_pexels_api_key: bool = False


def _home_dir() -> Path:
    return Path(os.path.expanduser(os.getenv("SMART_SLIDES_HOME", "~/.codex/smart-slides")))


def _env_path() -> Path:
    return _home_dir() / ".env"


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in _MANAGED_KEYS:
            continue
        if len(value) >= 2 and value[:1] in {"'", '"'} and value[-1:] == value[:1]:
            value = value[1:-1]
        values[key] = value
    return values


def _configured_values() -> dict[str, str]:
    values = _read_env_file(_env_path())
    for key in _MANAGED_KEYS:
        if os.getenv(key):
            values[key] = os.environ[key]
    return values


def _write_env_file(values: dict[str, str]) -> None:
    path = _env_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    previous = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    retained = [
        line
        for line in previous
        if not any(line.strip().removeprefix("export ").startswith(f"{key}=") for key in _MANAGED_KEYS)
    ]
    rendered = [*retained, *(f"{key}={values[key]}" for key in _MANAGED_KEYS if values.get(key))]
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".env.", delete=False) as handle:
        handle.write("\n".join(rendered) + ("\n" if rendered else ""))
        handle.flush()
        os.fchmod(handle.fileno(), 0o600)
        temporary = Path(handle.name)
    temporary.replace(path)
    path.chmod(0o600)


def _jogg_base_url() -> str:
    return os.getenv("JOGG_BASE_URL", "https://api.jogg.ai").rstrip("/")


def _validate_jogg(key: str) -> tuple[bool, str]:
    try:
        response = httpx.get(
            f"{_jogg_base_url()}/v2/user/whoami",
            headers={"X-Api-Key": key},
            timeout=10.0,
        )
    except httpx.HTTPError:
        return False, "Jogg 无法连接，请检查网络或稍后重试。"
    if response.is_success and response.headers.get("content-type", "").startswith("application/json"):
        try:
            payload: Any = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict) and payload.get("code") == 0 and isinstance(payload.get("data"), dict):
            return True, "Jogg API key 已验证。"
    return False, "Jogg 未接受此 API key。"


def _validate_pexels(key: str) -> tuple[bool, str]:
    try:
        response = httpx.get(
            "https://api.pexels.com/v1/search?query=technology&per_page=1",
            headers={"Authorization": key},
            timeout=10.0,
        )
    except httpx.HTTPError:
        return False, "Pexels 无法连接，已保存该 key。"
    if response.is_success:
        return True, "Pexels API key 已验证。"
    return False, "Pexels 未接受此 key，已保存以便稍后修正。"


@router.get("")
def get_settings() -> dict[str, object]:
    values = _configured_values()
    return {
        "jogg_api_key_configured": bool(values.get("JOGG_API_KEY")),
        "pexels_api_key_configured": bool(values.get("PEXELS_API_KEY")),
    }


@router.put("")
def update_settings(patch: SettingsPatch) -> dict[str, object]:
    values = _read_env_file(_env_path())
    submitted_jogg_key = patch.jogg_api_key.strip() if patch.jogg_api_key is not None else ""
    if submitted_jogg_key:
        jogg_valid, jogg_message = _validate_jogg(submitted_jogg_key)
        if not jogg_valid:
            raise HTTPException(status_code=422, detail=jogg_message)
        values["JOGG_API_KEY"] = submitted_jogg_key
    if patch.pexels_api_key is not None and patch.pexels_api_key.strip():
        values["PEXELS_API_KEY"] = patch.pexels_api_key.strip()
    if patch.clear_pexels_api_key:
        values.pop("PEXELS_API_KEY", None)
    if not values.get("JOGG_API_KEY") and not os.getenv("JOGG_API_KEY"):
        raise HTTPException(status_code=422, detail="JOGG_API_KEY is required")
    _write_env_file(values)
    jogg_key = values.get("JOGG_API_KEY") or os.getenv("JOGG_API_KEY", "")
    if submitted_jogg_key:
        jogg_valid, jogg_message = True, "Jogg API key 已验证。"
    else:
        jogg_valid, jogg_message = _validate_jogg(jogg_key)
    pexels_valid: bool | None = None
    pexels_message = "Pexels 未配置；自动 B-roll 下载将在缺少素材时暂停。"
    if values.get("PEXELS_API_KEY"):
        pexels_valid, pexels_message = _validate_pexels(values["PEXELS_API_KEY"])
    return {
        "saved": True,
        "jogg_valid": jogg_valid,
        "jogg_message": jogg_message,
        "pexels_valid": pexels_valid,
        "pexels_message": pexels_message,
        "restart_required": True,
    }
