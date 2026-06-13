import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import jieba


_FIELD_MAP = {
    "name": "name",
    "filename": "name",
    "path": "path",
    "dir": "parent_dir",
    "tag": "tags",
    "tags": "tags",
    "mime": "mime_type",
    "type": "mime_type",
    "ext": "ext",
    "size": "size",
    "mtime": "mtime",
    "date": "mtime",
    "owner": "owner",
    "content": "content",
}

_SIZE_UNITS = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}

_STOPWORDS = {
    "的", "了", "和", "是", "就", "都", "而", "及", "与", "着",
    "或", "一个", "没有", "我们", "你们", "他们", "它们", "这个",
    "那个", "这些", "那些", "但是", "如果", "因为", "所以", "虽然",
    "不", "也", "还", "又", "在", "于", "对", "从", "到", "把", "被",
    "让", "给", "向", "跟", "同", "为", "以", "中", "上", "下", "里",
    "外", "前", "后", "之", "等", "等等", "我", "你", "他", "她", "它",
    "这", "那", "吗", "呢", "吧", "啊", "呀", "哦", "嗯",
}

_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


@dataclass
class ParsedQuery:
    free_text: str = ""
    phrases: List[str] = field(default_factory=list)
    field_filters: List[Tuple[str, str, str]] = field(default_factory=list)
    clause_field_filters: List[List[Tuple[str, str, str]]] = field(default_factory=list)
    and_terms: List[str] = field(default_factory=list)
    or_terms: List[str] = field(default_factory=list)
    not_terms: List[str] = field(default_factory=list)
    clauses: List[List[str]] = field(default_factory=list)
    has_error: Optional[str] = None


def _normalize(text: str) -> str:
    if not text:
        return text
    return _PCT_RE.sub(lambda m: f"{m.group(0)} 百分之{m.group(1)}", text)


def _parse_size(val: str) -> Optional[int]:
    m = re.match(r"^\s*([><=]*)\s*([\d.]+)\s*([kmgt]?b?)\s*$", val, re.I)
    if not m:
        try:
            return int(float(val))
        except ValueError:
            return None
    op, num_str, unit = m.groups()
    try:
        num = float(num_str)
    except ValueError:
        return None
    u = unit.lower().rstrip("b") + "b" if unit else "b"
    if not u or u == "b":
        mult = 1
    else:
        mult = _SIZE_UNITS.get(u, 1)
    return int(num * mult)


def _parse_date(val: str) -> Optional[float]:
    val = val.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y%m%d"):
        try:
            return datetime.strptime(val, fmt).timestamp()
        except ValueError:
            continue
    try:
        return float(val)
    except ValueError:
        return None


def _tokenize_query(text: str) -> List[str]:
    text = _normalize(text)
    out = []
    for w in jieba.cut(text, cut_all=False):
        w = w.strip()
        if not w:
            continue
        if w in _STOPWORDS:
            continue
        if len(w) == 1 and not re.search(r"[\u4e00-\u9fffA-Za-z0-9%]", w):
            continue
        out.append(w)
    return out


_PUNCT_RE = re.compile(r"[，。！？、；：“”‘’（）《》【】,\.!\?;:\-_\"'()<>\[\]/\\]")


def _strip_punct(s: str) -> str:
    return _PUNCT_RE.sub(" ", s).strip()


def parse_query(raw: str) -> ParsedQuery:
    pq = ParsedQuery()
    if not raw:
        return pq
    pq.clauses.append([])  # clause 0: default AND group
    pq.clause_field_filters.append([])

    raw = raw.strip()
    tokens: List[str] = []
    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch == '"' or ch == "'":
            q = ch
            j = i + 1
            while j < n and raw[j] != q:
                j += 1
            if j < n:
                phrase = raw[i + 1:j].strip()
                if phrase:
                    pq.phrases.append(phrase)
                    pq.clauses[-1].extend(_tokenize_query(phrase))
                i = j + 1
                continue
            else:
                pq.has_error = "unclosed quote"
                break
        if ch.isspace():
            i += 1
            continue
        j = i
        while j < n and not raw[j].isspace():
            j += 1
        tok = raw[i:j]
        tokens.append(tok)
        i = j

    for tok in tokens:
        upper = tok.upper()
        if upper == "AND":
            continue
        if upper == "OR":
            pq.clauses.append([])
            pq.clause_field_filters.append([])
            continue
        if upper == "NOT":
            continue
        if tok.startswith("-") and len(tok) > 1:
            pq.not_terms.extend(_tokenize_query(tok[1:]))
            continue

        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$", tok)
        if m:
            f, v = m.group(1).lower(), m.group(2).strip().strip('"').strip("'")
            mapped = _FIELD_MAP.get(f)
            if mapped:
                if mapped in ("size", "mtime"):
                    cmp_op = "="
                    vm = re.match(r"^([><=!]+)\s*(.+)$", v)
                    if vm:
                        cmp_op = vm.group(1).replace("==", "=")
                        v = vm.group(2)
                    if mapped == "size":
                        nv = _parse_size(v)
                        if nv is not None:
                            entry = (mapped, cmp_op, str(nv))
                            pq.field_filters.append(entry)
                            pq.clause_field_filters[-1].append(entry)
                        else:
                            pq.clauses[-1].extend(_tokenize_query(tok))
                    else:
                        nv = _parse_date(v)
                        if nv is not None:
                            entry = (mapped, cmp_op, str(nv))
                            pq.field_filters.append(entry)
                            pq.clause_field_filters[-1].append(entry)
                        else:
                            pq.clauses[-1].extend(_tokenize_query(tok))
                else:
                    entry = (mapped, "=", v)
                    pq.field_filters.append(entry)
                    pq.clause_field_filters[-1].append(entry)
            else:
                pq.clauses[-1].extend(_tokenize_query(tok))
            continue

        pq.clauses[-1].extend(_tokenize_query(tok))

    # 清理空子句
    valid = [(i, c) for i, c in enumerate(pq.clauses) if c or pq.clause_field_filters[i]]
    if valid:
        keep_idx = {i for i, _ in valid}
        pq.clauses = [c for _, c in valid]
        pq.clause_field_filters = [
            ff for i, ff in enumerate(pq.clause_field_filters) if i in keep_idx
        ]
    else:
        pq.clauses = []
        pq.clause_field_filters = []
    # 扁平化到 and_terms / or_terms 以保持兼容
    seen: set = set()
    if len(pq.clauses) == 1:
        # 只有一个 AND 子句
        for w in pq.clauses[0]:
            if w not in seen:
                pq.and_terms.append(w)
                seen.add(w)
    elif len(pq.clauses) > 1:
        # 多个子句: OR(AND(group1), AND(group2), ...)
        # 简化: or_terms 存所有词(大OR), 同时 clauses 保留结构给 service 层
        for clause in pq.clauses:
            for w in clause:
                if w not in seen:
                    pq.or_terms.append(w)
                    seen.add(w)
        # 如果有 AND 组取交集作为 and_terms（所有子句公共词）
        if pq.clauses:
            common = set(pq.clauses[0])
            for c in pq.clauses[1:]:
                common &= set(c)
            for w in common:
                pq.and_terms.append(w)

    # 短语词加入 and_terms
    for phrase in pq.phrases:
        pw = _tokenize_query(phrase)
        for w in pw:
            if w not in seen:
                pq.and_terms.append(w)
                seen.add(w)

    # 去重 not_terms
    seen_not = set()
    pq.not_terms = [w for w in pq.not_terms if not (w in seen_not or seen_not.add(w))]

    free_parts = []
    for c in pq.clauses:
        free_parts.extend(c)
    if free_parts:
        pq.free_text = _strip_punct(" ".join(free_parts))

    return pq
