import sys
from pathlib import Path
_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJ_ROOT))

import json
from backend.index.manager import get_index_manager
from backend.search.service import search, SearchOptions
from backend.search.query_parser import parse_query

def test():
    im = get_index_manager()
    print("=" * 60)
    print("STEP 1: 增量索引构建")
    print("=" * 60)
    result = im.run_incremental_update()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    status = im.get_stats()
    print(f"\n索引状态: 已索引 {status['indexed_count']} 个文件, "
          f"失败 {status['failed_count']} 个")

    tests = [
        ("合同", {}, "基础关键词"),
        ("违约金不超过 30%", {}, "多词 AND"),
        ("\"不可抗力\" tag:法律", {}, "短语 + 字段限定"),
        ("name:合同 OR 设计稿", {}, "OR 逻辑"),
        ("搜索服务 -代码", {}, "NOT 排除"),
        ("mtime:>2024-01-01 size:>1KB", {}, "日期和大小限定"),
    ]

    print("\n" + "=" * 60)
    print("STEP 2: 搜索测试")
    print("=" * 60)
    for q, extra, label in tests:
        pq = parse_query(q)
        print(f"\n--- [{label}] q={q!r} ---")
        print(f"  parsed: AND={pq.and_terms} OR={pq.or_terms} NOT={pq.not_terms} "
              f"phrases={pq.phrases} fields={pq.field_filters}")
        opts = SearchOptions(q=q, **extra)
        resp = search(opts)
        print(f"  返回 {resp['total_returned']} 条结果, cursor={resp['cursor']}")
        for i, hit in enumerate(resp["results"][:3], 1):
            print(f"    [{i}] score={hit['score']:.3f} ocr_low={hit['ocr_low_conf']} "
                  f"name={hit['name']!r}")
            if hit["snippet_plain"]:
                s = hit["snippet_plain"].strip().replace("\n", " ")[:100]
                print(f"        snippet: {s!r}")

    print("\n✅ 全部完成")

if __name__ == "__main__":
    test()
