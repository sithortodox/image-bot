import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

INPUT_DIR = Path("storage/input")
OUTPUT_DIR = Path("storage/output")


def ensure_dirs() -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def is_allowed_image(filename: str | None) -> bool:
    if not filename:
        return False
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def input_path(ext: str) -> Path:
    ensure_dirs()
    return INPUT_DIR / f"{uuid.uuid4().hex}{ext}"


def output_path(ext: str = ".png") -> Path:
    ensure_dirs()
    return OUTPUT_DIR / f"{uuid.uuid4().hex}{ext}"


def safe_remove(path: str | Path | None) -> None:
    if not path:
        return
    p = Path(path)
    if p.exists() and p.is_file():
        p.unlink(missing_ok=True)
