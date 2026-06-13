import mimetypes
from pathlib import Path
from typing import Optional

_TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".log", ".ini", ".conf", ".cfg", ".yaml", ".yml",
    ".json", ".xml", ".html", ".htm", ".csv", ".tsv", ".env", ".toml",
}

_CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".cc", ".h",
    ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".sh", ".bash", ".zsh", ".bat", ".ps1", ".sql", ".vue", ".svelte", ".css",
    ".scss", ".less",
}

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp"}

_DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}


def guess_mime(path: str | Path) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    mime, _ = mimetypes.guess_type(str(p))

    if ext == ".pdf":
        return "application/pdf"
    if ext in (".doc", ".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if ext in (".ppt", ".pptx"):
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    if ext in (".xls", ".xlsx"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    if mime:
        return mime

    if ext in _TEXT_EXTENSIONS or ext in _CODE_EXTENSIONS:
        return "text/plain"
    if ext in _IMAGE_EXTENSIONS:
        return f"image/{ext.lstrip('.')}"
    return "application/octet-stream"


def is_text_mime(mime: str) -> bool:
    return mime.startswith("text/")


def is_code(path: str | Path) -> bool:
    return Path(path).suffix.lower() in _CODE_EXTENSIONS


def is_pdf(mime: str) -> bool:
    return "pdf" in mime


def is_office(mime: str) -> bool:
    return "officedocument" in mime or mime in (
        "application/msword",
        "application/vnd.ms-powerpoint",
        "application/vnd.ms-excel",
    )


def is_image(mime: str) -> bool:
    return mime.startswith("image/")


def is_ocr_candidate(mime: str, path: Optional[str | Path] = None) -> bool:
    if is_image(mime):
        return True
    if path and Path(path).suffix.lower() in _IMAGE_EXTENSIONS:
        return True
    return False


def category_of(mime: str, path: str | Path) -> str:
    ext = Path(path).suffix.lower()
    if is_pdf(mime):
        return "pdf"
    if is_office(mime):
        if ext in (".doc", ".docx"):
            return "docx"
        if ext in (".ppt", ".pptx"):
            return "pptx"
        if ext in (".xls", ".xlsx"):
            return "xlsx"
        return "office"
    if is_code(path):
        return "code"
    if is_image(mime):
        return "image"
    if is_text_mime(mime) or ext in _TEXT_EXTENSIONS:
        return "text"
    return "other"
