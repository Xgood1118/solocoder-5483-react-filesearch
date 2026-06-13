"""
搜索服务模块 - 演示代码文件按行索引
"""
from dataclasses import dataclass
from typing import List, Optional
import math
import jieba
from whoosh.query import And, Or, Term


@dataclass
class SearchOptions:
    q: str
    page: int = 1
    page_size: int = 20
    mime: Optional[str] = None
    path_prefix: Optional[str] = None


class BM25Scorer:
    """BM25 相关度计分器实现"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.avg_doc_len = 1200.0

    def score(self, tf: int, df: int, N: int, doc_len: int) -> float:
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
        norm = tf * (self.k1 + 1) / (
            tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
        )
        return idf * norm


def tokenize_cn(text: str) -> List[str]:
    """中文分词 + 停用词过滤"""
    words = []
    for w in jieba.cut(text, cut_all=False):
        w = w.strip()
        if w and len(w) >= 1:
            words.append(w)
    return words


def build_query(opts: SearchOptions):
    """构建查询：默认 AND 组合"""
    terms = tokenize_cn(opts.q)
    if not terms:
        return None
    clauses = [Or([Term("name", t), Term("content", t), Term("tags", t)]) for t in terms]
    return And(clauses)


if __name__ == "__main__":
    # 违约案例：用户搜「违约金 不超过 30%」
    options = SearchOptions(q="违约金 不超过 30%")
    query = build_query(options)
    print(f"查询构建完成: {query}")
