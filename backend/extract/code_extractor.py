import re
from pathlib import Path
from typing import List

from backend.config import MAX_CONTENT_LENGTH
from backend.extract.base import ExtractResult, CodeToken
from backend.extract.text_extractor import read_text
from backend.logger import logger

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[\u4e00-\u9fff]+|\d+")


def _tokenize_line(line: str, line_no: int) -> List[CodeToken]:
    tokens = []
    for m in _TOKEN_RE.finditer(line):
        tokens.append(
            CodeToken(token=m.group(0), line=line_no, column=m.start() + 1)
        )
    return tokens


def extract_code(path: str | Path) -> ExtractResult:
    p = Path(path)
    text = read_text(p)
    if text is None:
        return ExtractResult(success=False, error="code file decode failed")

    tokens: List[CodeToken] = []
    code_content_parts = []
    try:
        for lineno, line in enumerate(text.splitlines(), start=1):
            if len(line) > 5000:
                line = line[:5000]
            toks = _tokenize_line(line, lineno)
            tokens.extend(toks)
            if toks:
                code_content_parts.append(
                    " ".join(f"{t.token}@L{t.line}C{t.column}" for t in toks)
                )
    except Exception as e:
        logger.warning(f"code tokenize error {p}: {e}")
        return ExtractResult(success=False, error=f"tokenize: {e}")

    code_content = "\n".join(code_content_parts)
    if len(code_content) > MAX_CONTENT_LENGTH:
        code_content = code_content[:MAX_CONTENT_LENGTH]
        tokens = tokens[:80000]

    return ExtractResult(
        success=True,
        content=text,
        code_tokens=tokens,
        metadata={"code_index": code_content},
    )
