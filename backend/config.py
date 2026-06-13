import os
from pathlib import Path
from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parent
load_dotenv(_BASE_DIR / ".env")


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = (_BASE_DIR / p).resolve()
    return p


FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

INDEX_DIR = _resolve(os.getenv("INDEX_DIR", "../data/index"))
LOG_DIR = _resolve(os.getenv("LOG_DIR", "../data/logs"))
STATS_DIR = _resolve(os.getenv("STATS_DIR", "../data/stats"))
FILES_ROOT_DIR = _resolve(os.getenv("FILES_ROOT_DIR", "../sample_files"))
JIEBA_DICT_PATH = _resolve(os.getenv("JIEBA_DICT_PATH", "./extract/custom_dict.txt"))
OCR_LANG = os.getenv("OCR_LANG", "chi_sim+eng")
OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"
CORS_ORIGIN_RAW = os.getenv(
    "CORS_ORIGIN",
    "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5174",
)
CORS_ORIGIN = [s.strip() for s in CORS_ORIGIN_RAW.split(",") if s.strip()]

MAX_CONTENT_LENGTH = 2_000_000
OCR_QUEUE_MAX = 1000
SEARCH_PAGE_SIZE_DEFAULT = 20
SEARCH_PAGE_SIZE_MAX = 100
SEARCH_HISTORY_TOP_N = 50
STATS_TOP_K = 20

for _d in (INDEX_DIR, LOG_DIR, STATS_DIR, FILES_ROOT_DIR):
    _d.mkdir(parents=True, exist_ok=True)
