import base64
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from whoosh import query as wq
from whoosh.qparser import MultifieldParser, QueryParser
from whoosh.query import (
    And,
    Every,
    Not,
    NumericRange,
    Or,
    Phrase,
    Prefix,
    Term,
    TermRange,
)

from backend.config import (
    SEARCH_PAGE_SIZE_DEFAULT,
    SEARCH_PAGE_SIZE_MAX,
    STATS_TOP_K,
)
from backend.index.manager import get_index_manager
from backend.index.schema import FIELD_WEIGHTS, make_bm25f_weighting
from backend.logger import logger
from backend.search.highlighter import (
    escape_html_full,
    extract_snippet_plain,
    highlight_keywords,
)
from backend.search.query_parser import parse_query


def _tokenize_for_field(val: str) -> List[str]:
    import jieba
    out = []
    for w in jieba.cut(val, cut_all=False):
        w = w.strip()
        if not w:
            continue
        out.append(w)
        if len(w) >= 2 and any("\u4e00" <= ch <= "\u9fff" for ch in w):
            for ch in w:
                out.append(ch)
    seen = set()
    uniq = []
    for w in out:
        if w not in seen:
            uniq.append(w)
            seen.add(w)
    return uniq


def _make_field_filter_query(f: str, op: str, v: str) -> "wq.Query":
    from whoosh.query import NumericRange, Not, Or, Prefix, Term

    if f in ("size", "mtime"):
        val = float(v) if "." in v else int(v)
        if op == ">":
            return NumericRange(f, start=val, end=None, startexcl=True)
        if op == ">=":
            return NumericRange(f, start=val, end=None)
        if op == "<":
            return NumericRange(f, start=None, end=val, endexcl=True)
        if op == "<=":
            return NumericRange(f, start=None, end=val)
        if op == "!=":
            return Not(NumericRange(f, start=val, end=val))
        return NumericRange(f, start=val, end=val)
    if f == "mime_type":
        if "/" in v:
            return Or([Term(f, v), Prefix(f, v)])
        return Prefix(f, v)
    if f == "tags":
        tag_terms = _tokenize_for_field(v)
        if not tag_terms:
            return Prefix(f, v)
        return Or(
            [Prefix(f, t) for t in tag_terms] + [Term(f, t) for t in tag_terms]
        )
    if f == "ext":
        return Or([Term(f, v.lower()), Prefix(f, v.lower())])
    if f == "owner":
        return Or([Term(f, v), Prefix(f, v)])
    if f == "parent_dir":
        return Prefix("path", v)
    if f == "path":
        path_terms = _tokenize_for_field(v)
        if path_terms:
            return And(
                [Or([Prefix("path", t), Term("path", t)]) for t in path_terms]
            )
        return Prefix("path", v)
    if f == "name":
        name_terms = _tokenize_for_field(v)
        if name_terms:
            return And(
                [Or([Term("name", t), Prefix("name", t)]) for t in name_terms]
            )
        return Prefix("name", v)
    return Prefix(f, v)


RECENCY_BOOST = 0.5
_SNIPPET_WINDOW = 60
_MAX_HITS = 5000


@dataclass
class SearchOptions:
    q: str
    path_prefix: str = ""
    mime: str = ""
    from_date: Optional[float] = None
    to_date: Optional[float] = None
    page: int = 1
    page_size: int = SEARCH_PAGE_SIZE_DEFAULT
    cursor: Optional[str] = None


def _build_whoosh_query(pq, schema, opts: SearchOptions) -> "wq.Query":
    content_fields = ["name", "path", "content", "tags", "code_index"]
    MultifieldParser(content_fields, schema)
    all_clauses: List[wq.Query] = []

    def _field_or(term: str) -> wq.Query:
        return Or([Prefix(f, term) for f in content_fields])

    clauses_struct = getattr(pq, "clauses", None) or []
    clause_field_filters_struct = getattr(pq, "clause_field_filters", None) or []

    if clauses_struct or clause_field_filters_struct:
        n_clauses = max(len(clauses_struct), len(clause_field_filters_struct))
        clause_queries: List[wq.Query] = []
        for i in range(n_clauses):
            terms = clauses_struct[i] if i < len(clauses_struct) else []
            filters = clause_field_filters_struct[i] if i < len(clause_field_filters_struct) else []
            parts: List[wq.Query] = []
            for t in terms:
                parts.append(_field_or(t))
            for f, op, v in filters:
                parts.append(_make_field_filter_query(f, op, v))
            if not parts:
                continue
            q = And(parts) if len(parts) > 1 else parts[0]
            clause_queries.append(q)
        if clause_queries:
            if len(clause_queries) == 1:
                all_clauses.append(clause_queries[0])
            else:
                all_clauses.append(Or(clause_queries))
    else:
        # 兼容：没有 clauses 结构，用原来的扁平结构
        free_terms = pq.and_terms
        if free_terms:
            if len(free_terms) == 1:
                term = free_terms[0]
                free_q = _field_or(term)
            else:
                tc_groups = [_field_or(term) for term in free_terms]
                free_q = And(tc_groups)
            all_clauses.append(free_q)
        if pq.or_terms:
            tc = [_field_or(term) for term in pq.or_terms]
            all_clauses.append(Or(tc))
        for f, op, v in pq.field_filters:
            all_clauses.append(_make_field_filter_query(f, op, v))

    for phrase in pq.phrases:
        words = list(phrase) if all(ord(c) > 127 for c in phrase) else phrase.split()
        if words:
            all_clauses.append(Or([Phrase("content", words), Phrase("name", words)]))

    for not_term in pq.not_terms:
        all_clauses.append(Not(_field_or(not_term)))

    if opts.path_prefix:
        all_clauses.append(Prefix("path", opts.path_prefix))
    if opts.mime:
        all_clauses.append(Prefix("mime_type", opts.mime))
    if opts.from_date is not None:
        all_clauses.append(NumericRange("mtime", start=float(opts.from_date), end=None))
    if opts.to_date is not None:
        all_clauses.append(NumericRange("mtime", start=None, end=float(opts.to_date)))

    if not all_clauses:
        return Every()
    if len(all_clauses) == 1:
        return all_clauses[0]
    return And(all_clauses)


def _rescore(hit_score: float, hit: Dict) -> float:
    mtime = float(hit.get("mtime") or 0)
    if mtime > 0:
        age_days = max(0.0, (time.time() - mtime) / 86400.0)
        decay = math.exp(-age_days / 365.0)
        recency_boost = 1.0 + RECENCY_BOOST * decay
    else:
        recency_boost = 1.0
    return hit_score * recency_boost


def _encode_cursor(last_score: float, last_file_id: str) -> str:
    raw = f"{last_score:.9f}|{last_file_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> Optional[Dict]:
    try:
        pad = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(cursor + pad).decode("utf-8")
        score_str, fid = raw.split("|", 1)
        return {"score": float(score_str), "file_id": fid}
    except Exception:
        return None


def search(opts: SearchOptions) -> Dict[str, Any]:
    im = get_index_manager()
    ix = im.ix
    pq = parse_query(opts.q)

    opts.page_size = min(max(1, opts.page_size), SEARCH_PAGE_SIZE_MAX)

    with ix.searcher(weighting=make_bm25f_weighting()) as s:
        q = _build_whoosh_query(pq, ix.schema, opts)
        try:
            results = s.search(q, limit=_MAX_HITS, terms=True)
        except Exception as e:
            logger.warning(f"search execution failed: {e}; q={opts.q!r}")
            return {"results": [], "cursor": None, "parsed": _parsed_info(pq), "total_returned": 0, "error": str(e)}

        rescored = []
        for h in results:
            d = dict(h)
            original_score = float(h.score)
            final_score = _rescore(original_score, d)
            all_terms: List[str] = []
            try:
                matched = h.matched_terms()
                for t in matched:
                    _, term = t
                    ts = term.decode("utf-8") if isinstance(term, bytes) else str(term)
                    if len(ts) >= 1:
                        all_terms.append(ts)
            except Exception:
                pass
            kw = list(dict.fromkeys(pq.and_terms + pq.or_terms + pq.phrases + all_terms))
            rescored.append((final_score, d, kw))

        rescored.sort(key=lambda x: x[0], reverse=True)

        start_idx = 0
        if opts.cursor:
            cur = _decode_cursor(opts.cursor)
            if cur:
                for i, (sc, d, _) in enumerate(rescored):
                    if sc < cur["score"] - 1e-9 or (
                        abs(sc - cur["score"]) < 1e-9 and d.get("file_id", "") > cur["file_id"]
                    ):
                        start_idx = i
                        break
                else:
                    start_idx = len(rescored)

        end_idx = min(len(rescored), start_idx + opts.page_size)
        page_items = rescored[start_idx:end_idx]

        out_results = []
        all_keywords = list(dict.fromkeys(pq.and_terms + pq.or_terms + pq.phrases))
        for final_score, d, kw in page_items:
            content = d.get("content_stored") or extract_snippet_plain(d.get("name", "") + " " + d.get("path", ""), all_keywords, window=20)
            snippet_html, hit_positions = highlight_keywords(
                content or d.get("name", ""),
                kw or all_keywords,
                window=_SNIPPET_WINDOW,
            )
            out_results.append({
                "file_id": d.get("file_id"),
                "path": d.get("path"),
                "name": d.get("name"),
                "size": d.get("size"),
                "mtime": d.get("mtime"),
                "mime_type": d.get("mime_type"),
                "owner": d.get("owner"),
                "tags": [t for t in (d.get("tags") or "").split(",") if t],
                "ext": d.get("ext"),
                "score": round(final_score, 4),
                "bm25_score": round(final_score / max(1e-9, _rescore(1.0, d) / 1.0), 4),
                "snippet_html": snippet_html,
                "snippet_plain": extract_snippet_plain(content or d.get("name", ""), kw or all_keywords),
                "hit_positions": hit_positions[:20],
                "ocr_low_conf": bool(d.get("ocr_low_conf")),
                "field_weights": FIELD_WEIGHTS,
            })

        next_cursor = None
        if end_idx < len(rescored):
            last_score, last_doc, _ = rescored[end_idx - 1]
            next_cursor = _encode_cursor(last_score, last_doc.get("file_id", ""))

    return {
        "results": out_results,
        "cursor": next_cursor,
        "parsed": _parsed_info(pq),
        "total_returned": len(out_results),
        "total_found_cap": _MAX_HITS,
    }


def _parsed_info(pq) -> Dict:
    return {
        "free_text": pq.free_text,
        "phrases": pq.phrases,
        "and_terms": pq.and_terms,
        "or_terms": pq.or_terms,
        "not_terms": pq.not_terms,
        "clauses": getattr(pq, "clauses", []),
        "field_filters": pq.field_filters,
        "error": pq.has_error,
    }
