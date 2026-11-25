import uuid
from pathlib import Path
from typing import BinaryIO, Protocol

from app.core.config import get_settings


class FileStorage(Protocol):
    """Storage contract. Swap LocalFileStorage for e.g. S3FileStorage without touching services."""

    def save(self, file: BinaryIO, original_name: str) -> str: ...

    def delete(self, path: str) -> None: ...


class LocalFileStorage:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file: BinaryIO, original_name: str) -> str:
        # Random name: avoids collisions and never trusts the client's filename as a path.
        target = self.base_dir / f"{uuid.uuid4().hex}{Path(original_name).suffix.lower()}"
        with target.open("wb") as out:
            while chunk := file.read(1024 * 1024):
                out.write(chunk)
        return str(target)

    def delete(self, path: str) -> None:
        Path(path).unlink(missing_ok=True)


def get_storage() -> FileStorage:
    return LocalFileStorage(get_settings().upload_dir)
