import re
from typing import Iterable, List

import jieba

from backend.config import JIEBA_DICT_PATH
from backend.logger import logger
from whoosh.analysis import (
    CharsetFilter,
    LowercaseFilter,
    RegexTokenizer,
    StopFilter,
    Token,
    Tokenizer,
)
from whoosh.util.text import rcompile

try:
    if JIEBA_DICT_PATH.exists():
        jieba.load_userdict(str(JIEBA_DICT_PATH))
        logger.info(f"loaded jieba user dict: {JIEBA_DICT_PATH}")
except Exception as e:
    logger.warning(f"jieba user dict load failed: {e}")

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_WORD_RE = rcompile(r"[A-Za-z0-9_][A-Za-z0-9_%\-]*|[\u4e00-\u9fff]+")

_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_NUM_UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(百|千|万|亿|MB|KB|GB|TB|mb|kb|gb|tb)")

_STOPWORDS = {
    "的", "了", "和", "是", "就", "都", "而", "及", "与", "着",
    "或", "一个", "没有", "我们", "你们", "他们", "它们", "这个",
    "那个", "这些", "那些", "但是", "如果", "因为", "所以", "虽然",
    "不", "也", "还", "又", "在", "于", "对", "从", "到", "把", "被",
    "让", "给", "向", "跟", "同", "为", "以", "中", "上", "下", "里",
    "外", "前", "后", "之", "等", "等等",
}


def _normalize(text: str) -> str:
    if not text:
        return text
    t = _PCT_RE.sub(lambda m: f"{m.group(0)} 百分之{m.group(1)}", text)
    t = _NUM_UNIT_RE.sub(lambda m: f"{m.group(0)} {m.group(1)}{m.group(2)}", t)
    return t


class JiebaTokenizer(Tokenizer):
    def __call__(self, value, positions=False, chars=False, keeporiginal=False,
                 removestops=True, start_pos=0, start_char=0, mode='', **kwargs):
        assert isinstance(value, str), f"{type(value)}"
        value = _normalize(value)
        t = Token(positions, chars, removestops=removestops, mode=mode, **kwargs)
        if not value:
            return
        pos = start_pos
        char = start_char
        for seg in jieba.cut(value, cut_all=False):
            seg = seg.strip()
            if not seg:
                continue
            if seg in _STOPWORDS and removestops:
                pos += 1
                continue
            if _CJK_RE.search(seg):
                for ch in seg:
                    t.text = ch
                    t.boost = 1.0
                    if positions:
                        t.pos = pos
                        pos += 1
                    if chars:
                        idx = value.find(ch, char)
                        if idx >= 0:
                            t.startchar = idx
                            t.endchar = idx + 1
                            char = idx + 1
                    yield t
                joined_text = "".join(seg)
                if len(joined_text) >= 2:
                    t.text = joined_text
                    t.boost = 1.2
                    if positions:
                        t.pos = pos
                        pos += 1
                    if chars:
                        idx = value.find(joined_text, char)
                        if idx >= 0:
                            t.startchar = idx
                            t.endchar = idx + len(joined_text)
                            char = idx + len(joined_text)
                    yield t
            else:
                t.text = seg.lower()
                t.boost = 1.0
                if positions:
                    t.pos = pos
                    pos += 1
                if chars:
                    idx = value.lower().find(t.text.lower(), char)
                    if idx >= 0:
                        t.startchar = idx
                        t.endchar = idx + len(seg)
                        char = idx + len(seg)
                yield t


def jieba_analyzer():
    return JiebaTokenizer() | LowercaseFilter()


def standard_analyzer():
    return RegexTokenizer(_WORD_RE) | LowercaseFilter() | StopFilter()

