import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile


task_root = Path(__file__).resolve().parents[1]
catalog_path = task_root / "jogg-npm/packages/smartvideo/resources/avatar-packs.json"
resource = next(item for item in json.loads(catalog_path.read_text())["resources"] if item["resource_id"] == "office-presenter")
source_root = "smart-video-avatar-office-presenter-1.0.0"
source_url = "https://github.com/JoggAI-Tech/jogg-skills/releases/download/smart-video-avatar-office-presenter-v1.0.0/" + source_root + ".tar.gz"
source_sha256 = "71f8db719131c066444d7b25558334ae12d407cb999205980b3896bc0f105770"
output = task_root / "artifacts/avatar-office-presenter-1.0.1"
output.mkdir(parents=True, exist_ok=True)
source = output / "original-1.0.0.tar.gz"
archive = output / "smart-video-avatar-office-presenter-1.0.1.tar.gz"
new_root = "smart-video-avatar-office-presenter-1.0.1"


def digest(file):
    with file.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


if not source.exists():
    subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error", "--output", str(source), source_url], check=True)
assert digest(source) == source_sha256, "Original archive checksum mismatch"
assert not (output / "release.json").exists() or json.loads((output / "release.json").read_text())["status"] != "published", "Never rebuild published resource archives"
payload = {}
skipped = []
with source.open("rb") as input_file, archive.open("wb") as output_file:
    with gzip.GzipFile(filename="", fileobj=output_file, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=input_file, mode="r|gz") as original, tarfile.open(fileobj=zipped, mode="w|") as cleaned:
            for member in original:
                parts = PurePosixPath(member.name).parts
                assert not member.name.startswith("/") and ".." not in parts
                if any(part.startswith("._") or part in {"__MACOSX", ".DS_Store"} for part in parts):
                    skipped.append(member.name)
                    continue
                assert parts and parts[0] == source_root, member.name
                assert member.isdir() or member.isfile(), member.name
                relative = "/".join(parts[1:])
                info = tarfile.TarInfo(new_root + ("/" + relative if relative else ""))
                info.type = tarfile.DIRTYPE if member.isdir() else tarfile.REGTYPE
                info.mode = member.mode & 0o777
                info.size = member.size if member.isfile() else 0
                if member.isfile():
                    with original.extractfile(member) as data:
                        content = data.read()
                    payload[relative] = hashlib.sha256(content).hexdigest()
                    cleaned.addfile(info, io.BytesIO(content))
                else:
                    cleaned.addfile(info)

verified = {}
with tarfile.open(archive, "r:gz") as checked:
    for member in checked:
        assert not any(part.startswith("._") or part in {"__MACOSX", ".DS_Store"} for part in PurePosixPath(member.name).parts)
        assert member.name == new_root or member.name.startswith(new_root + "/")
        if member.isfile():
            with checked.extractfile(member) as data:
                verified[member.name[len(new_root) + 1:]] = hashlib.file_digest(data, "sha256").hexdigest()
assert verified == payload, "Resource file contents changed during repack"
report = {
    "status": "prepared", "resource_id": resource["resource_id"], "version": "1.0.1",
    "filename": archive.name, "archive_root": new_root, "sha256": digest(archive),
    "bytes": archive.stat().st_size, "source_sha256": source_sha256,
    "payload_files": len(payload), "skipped_metadata_entries": len(skipped),
    "payload_contents_unchanged": True, "tag": "smart-video-avatar-office-presenter-v1.0.1",
    "archive_url": "https://github.com/JoggAI-Tech/jogg-skills/releases/download/smart-video-avatar-office-presenter-v1.0.1/" + archive.name,
}
(output / "release.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
