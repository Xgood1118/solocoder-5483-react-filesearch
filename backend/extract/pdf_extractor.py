from pathlib import Path
from typing import List

from backend.config import MAX_CONTENT_LENGTH
from backend.extract.base import ExtractResult
from backend.extract.ocr_extractor import OCRTask, ocr_queue
from backend.logger import logger


def _is_scanned_page(text: str, threshold: int = 10) -> bool:
    cleaned = text.replace(" ", "").replace("\n", "").replace("\t", "")
    return len(cleaned.strip()) < threshold


def extract_pdf(path: str | Path) -> ExtractResult:
    p = Path(path)
    try:
        from pypdf import PdfReader
    except ImportError:
        return ExtractResult(success=False, error="pypdf not installed")

    try:
        reader = PdfReader(str(p))
    except Exception as e:
        logger.warning(f"open pdf failed {p}: {e}")
        return ExtractResult(success=False, error=f"open pdf: {e}")

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            return ExtractResult(success=False, error="pdf is encrypted")

    pages_text: List[str] = []
    ocr_pages: List[int] = []
    has_scanned = False

    try:
        total_pages = len(reader.pages)
    except Exception as e:
        return ExtractResult(success=False, error=f"pdf pages count: {e}")

    for i in range(total_pages):
        try:
            page = reader.pages[i]
            text = page.extract_text() or ""
            if _is_scanned_page(text):
                has_scanned = True
                ocr_pages.append(i + 1)
            pages_text.append(text)
        except Exception as e:
            logger.warning(f"pdf page {i} extract error {p}: {e}")
            pages_text.append("")

    combined = "\n\n".join(pages_text)
    if len(combined) > MAX_CONTENT_LENGTH:
        combined = combined[:MAX_CONTENT_LENGTH]

    if has_scanned:
        task = OCRTask(p, page=0)
        ocr_queue.submit(task)

    return ExtractResult(
        success=True,
        content=combined,
        ocr_pages=ocr_pages,
        ocr_confidence_low=has_scanned,
        metadata={"total_pages": total_pages, "scanned_pages": len(ocr_pages)},
    )
