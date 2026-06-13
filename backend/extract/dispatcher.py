from pathlib import Path

from backend.extract.base import ExtractResult
from backend.extract.code_extractor import extract_code
from backend.extract.office_extractor import extract_docx, extract_pptx, extract_xlsx
from backend.extract.ocr_extractor import OCRTask, ocr_queue
from backend.extract.pdf_extractor import extract_pdf
from backend.extract.text_extractor import extract_text
from backend.logger import logger
from backend.mime_utils import category_of, guess_mime, is_ocr_candidate


def dispatch(path: str | Path, mime: str | None = None) -> ExtractResult:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ExtractResult(success=False, error="file not found")

    mime = mime or guess_mime(p)
    cat = category_of(mime, p)

    try:
        if cat == "pdf":
            return extract_pdf(p)
        if cat == "docx":
            return extract_docx(p)
        if cat == "pptx":
            return extract_pptx(p)
        if cat == "xlsx":
            return extract_xlsx(p)
        if cat == "code":
            return extract_code(p)
        if cat == "image":
            if is_ocr_candidate(mime, p):
                task = OCRTask(p, page=0)
                ok = ocr_queue.submit(task)
                return ExtractResult(
                    success=True,
                    content="",
                    ocr_pages=[0],
                    ocr_confidence_low=True,
                    metadata={"ocr_submitted": ok, "ocr_in_progress": ok},
                )
            return ExtractResult(success=True, content="")
        if cat == "text":
            return extract_text(p)
        return extract_text(p)
    except Exception as e:
        logger.exception(f"dispatch unexpected error {p}: {e}")
        return ExtractResult(success=False, error=f"unexpected: {e}")
