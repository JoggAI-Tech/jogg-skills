import os
import shutil
from dataclasses import dataclass
from typing import Optional


DATA_DIR = os.path.expanduser(os.getenv("SMART_SLIDES_DATA_DIR", "~/.codex/smart-slides/data"))


@dataclass
class StoredFile:
    path: str
    url: str
    key: str
    backend: str = "local"
    mime: str = "application/octet-stream"


def set_data_dir_for_tests(data_dir: str) -> None:
    global DATA_DIR
    DATA_DIR = data_dir


def storage_backend() -> str:
    return "local"


def is_cloud_storage_enabled() -> bool:
    return False


def _normalize_key(key: str) -> str:
    parts = [part for part in str(key or "").replace("\\", "/").lstrip("/").split("/") if part and part not in {".", ".."}]
    if not parts:
        raise ValueError("storage key is required")
    return "/".join(parts)


def path_for_key(key: str) -> str:
    return os.path.join(DATA_DIR, _normalize_key(key))


def save_bytes(key: str, content: bytes, mime: Optional[str] = None) -> StoredFile:
    normalized = _normalize_key(key)
    path = path_for_key(normalized)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as file:
        file.write(content)
    return StoredFile(path=path, url=f"/data/{normalized}", key=normalized, mime=mime or "application/octet-stream")


def upload_file(key: str, local_path: str, mime: Optional[str] = None) -> StoredFile:
    normalized = _normalize_key(key)
    destination = path_for_key(normalized)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    if os.path.abspath(local_path) != os.path.abspath(destination):
        shutil.copyfile(local_path, destination)
    return StoredFile(path=destination, url=f"/data/{normalized}", key=normalized, mime=mime or "application/octet-stream")


def delete_path(path: str) -> None:
    if path and os.path.isfile(path):
        os.remove(path)


def ensure_local_file(path: str) -> str:
    if path.startswith("/data/"):
        return path_for_key(path[len("/data/") :])
    return path
