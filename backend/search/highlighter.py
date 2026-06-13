import html
import re
from typing import Iterable, List, Optional, Tuple

import jieba


def escape_html_full(text: str) -> str:
    return html.escape(text, quote=True)


_SAFE_ATTR_RE = re.compile(r"^\s*on\w+\s*=", re.I)


def _contains_event_injection(text: str) -> bool:
    return bool(_SAFE_ATTR_RE.search(text))


def highlight_keywords(
    content: str,
    keywords: Iterable[str],
    *,
    window: int = 60,
    max_snippets: int = 3,
    tag: str = "mark",
    attrs: str = "",
) -> Tuple[str, List[Tuple[int, int]]]:
    if not content:
        return "", []
    if attrs:
        if _contains_event_injection(attrs) or "javascript:" in attrs.lower():
            attrs = ""
    kw_list = [k for k in keywords if k]
    if not kw_list:
        return escape_html_full(content[: window * 4]), []

    safe_kws = []
    for k in kw_list:
        sk = escape_html_full(k)
        safe_kws.append(sk)

    pattern_parts = []
    for k in kw_list:
        if len(k) == 1:
            pattern_parts.append(re.escape(k))
        else:
            segs = list(jieba.cut(k))
            if len(segs) > 1:
                pattern_parts.append("|".join(re.escape(s) for s in segs if s))
            pattern_parts.append(re.escape(k))
    pattern = re.compile("|".join(p for p in pattern_parts if p), re.IGNORECASE)

    positions: List[Tuple[int, int]] = []
    for m in pattern.finditer(content):
        positions.append((m.start(), m.end()))
    if not positions:
        snippet = content[: window * 2]
        return escape_html_full(snippet), []

    covered = []
    snippets_ranges: List[Tuple[int, int]] = []
    for start, end in positions:
        overlap = False
        for cs, ce in covered:
            if start - window <= ce and end + window >= cs:
                overlap = True
                break
        if not overlap:
            s_start = max(0, start - window)
            s_end = min(len(content), end + window)
            snippets_ranges.append((s_start, s_end))
            covered.append((s_start, s_end))
            if len(snippets_ranges) >= max_snippets:
                break

    out_parts: List[str] = []
    for s_start, s_end in snippets_ranges:
        seg = content[s_start:s_end]
        safe = escape_html_full(seg)
        def _sub(m):
            return f"<{tag}{(' ' + attrs) if attrs else ''}>{m.group(0)}</{tag}>"
        highlighted = pattern.sub(_sub, safe)
        out_parts.append(highlighted)

    return ("<br><span>...</span><br>".join(out_parts)) if out_parts else escape_html_full(content[: window * 4]), positions


def extract_snippet_plain(content: str, keywords: Iterable[str], window: int = 40) -> str:
    if not content:
        return ""
    kw_list = [k for k in keywords if k]
    if not kw_list:
        return content[: window * 4]
    pattern_parts = [re.escape(k) for k in kw_list]
    try:
        pattern = re.compile("|".join(pattern_parts), re.IGNORECASE)
    except re.error:
        return content[: window * 4]
    m = pattern.search(content)
    if not m:
        return content[: window * 4]
    s = max(0, m.start() - window)
    e = min(len(content), m.end() + window)
    return content[s:e]
