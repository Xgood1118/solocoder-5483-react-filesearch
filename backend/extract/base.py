from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class CodeToken:
    token: str
    line: int
    column: int


@dataclass
class ExtractResult:
    success: bool
    content: str = ""
    code_tokens: List[CodeToken] = field(default_factory=list)
    ocr_pages: List[int] = field(default_factory=list)
    ocr_confidence_low: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
