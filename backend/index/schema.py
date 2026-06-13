from whoosh import fields
from whoosh.scoring import BM25F
from backend.index.analyzer import jieba_analyzer, standard_analyzer


FIELD_WEIGHTS = {
    "name": 3.0,
    "path": 2.0,
    "content": 1.0,
    "tags": 2.0,
    "code_index": 1.0,
}


def make_schema():
    return fields.Schema(
        file_id=fields.ID(unique=True, stored=True),
        path=fields.TEXT(analyzer=standard_analyzer(), stored=True, field_boost=FIELD_WEIGHTS["path"]),
        name=fields.TEXT(analyzer=jieba_analyzer(), stored=True, field_boost=FIELD_WEIGHTS["name"]),
        content=fields.TEXT(analyzer=jieba_analyzer(), stored=False, field_boost=FIELD_WEIGHTS["content"]),
        content_stored=fields.STORED(),
        size=fields.NUMERIC(int, 64, stored=True, signed=False),
        mtime=fields.NUMERIC(float, 64, stored=True, signed=True),
        mime_type=fields.ID(stored=True),
        owner=fields.ID(stored=True),
        tags=fields.KEYWORD(stored=True, commas=True, scorable=True, field_boost=FIELD_WEIGHTS["tags"]),
        code_index=fields.TEXT(analyzer=standard_analyzer(), stored=False, field_boost=FIELD_WEIGHTS["code_index"]),
        ocr_low_conf=fields.BOOLEAN(stored=True),
        ext=fields.ID(stored=True),
        parent_dir=fields.ID(stored=True),
    )


def make_bm25f_weighting() -> BM25F:
    return BM25F(B=0.75, K1=1.5,
                 field_B={"name": 0.5, "path": 0.6, "content": 0.75, "tags": 0.5, "code_index": 0.75})
