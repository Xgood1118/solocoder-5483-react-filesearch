from pathlib import Path
from typing import Optional

from backend.config import MAX_CONTENT_LENGTH
from backend.extract.base import ExtractResult
from backend.logger import logger


_ENCODINGS = ["utf-8", "utf-8-sig", "gbk", "gb18030", "latin-1", "cp1252"]


def read_text(path: str | Path, max_len: int = MAX_CONTENT_LENGTH) -> Optional[str]:
    p = Path(path)
    try:
        raw = p.read_bytes()
    except Exception as e:
        logger.warning(f"read_text failed to read {p}: {e}")
        return None

    for enc in _ENCODINGS:
        try:
            text = raw.decode(enc, errors="strict")
            if len(text) > max_len:
                text = text[:max_len]
            return text
        except (UnicodeDecodeError, LookupError):
            continue

    try:
        text = raw.decode("utf-8", errors="replace")
        return text[:max_len] if len(text) > max_len else text
    except Exception as e:
        logger.warning(f"read_text decode fallback failed {p}: {e}")
        return None


def extract_text(path: str | Path) -> ExtractResult:
    text = read_text(path)
    if text is None:
        return ExtractResult(success=False, error="text decode failed")
    return ExtractResult(success=True, content=text)
