import json
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from backend.config import STATS_DIR, STATS_TOP_K
from backend.logger import logger


class StatsStore:
    def __init__(self, stats_dir: Path = STATS_DIR):
        self.dir = Path(stats_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._term_file = self.dir / "search_terms.json"
        self._hit_file = self.dir / "file_hits.json"
        self._qps_file = self.dir / "qps.json"

        self.term_counter: Counter = Counter()
        self.hit_counter: Counter = Counter()
        self._qps_buckets: Dict[str, int] = defaultdict(int)
        self._load()

    def _load(self):
        for path, attr, ctor in [
            (self._term_file, "term_counter", Counter),
            (self._hit_file, "hit_counter", Counter),
        ]:
            try:
                if path.exists():
                    data = json.loads(path.read_text(encoding="utf-8"))
                    setattr(self, attr, ctor(data))
            except Exception as e:
                logger.warning(f"load stats {path} failed: {e}")
                setattr(self, attr, ctor())

        try:
            if self._qps_file.exists():
                raw = json.loads(self._qps_file.read_text(encoding="utf-8"))
                self._qps_buckets = defaultdict(int, raw)
        except Exception as e:
            logger.warning(f"load qps stats failed: {e}")
            self._qps_buckets = defaultdict(int)

    def _persist(self):
        try:
            self._term_file.write_text(
                json.dumps(dict(self.term_counter), ensure_ascii=False), encoding="utf-8"
            )
            self._hit_file.write_text(
                json.dumps(dict(self.hit_counter), ensure_ascii=False), encoding="utf-8"
            )
            self._qps_file.write_text(
                json.dumps(dict(self._qps_buckets), ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"persist stats failed: {e}")

    def record_search(self, q: str, result_file_ids: List[str]):
        if not q:
            return
        q = q.strip()
        if not q:
            return
        with self._lock:
            self.term_counter[q] += 1
            for fid in result_file_ids:
                if fid:
                    self.hit_counter[fid] += 1
            minute_bucket = time.strftime("%Y-%m-%d %H:%M")
            self._qps_buckets[minute_bucket] += 1
            if len(self.term_counter) % 50 == 0:
                self._persist()

    def top_terms(self, k: int = STATS_TOP_K) -> List[Dict[str, Any]]:
        with self._lock:
            items = self.term_counter.most_common(k)
        return [{"term": t, "count": c} for t, c in items]

    def top_files(self, file_label_map: Dict[str, str], k: int = STATS_TOP_K) -> List[Dict[str, Any]]:
        with self._lock:
            items = self.hit_counter.most_common(k)
        out = []
        for fid, c in items:
            out.append({"file_id": fid, "label": file_label_map.get(fid, fid), "count": c})
        return out

    def qps_summary(self) -> Dict[str, Any]:
        with self._lock:
            buckets = dict(self._qps_buckets)
        if not buckets:
            return {"per_minute": [], "total_last_hour": 0, "total_last_day": 0, "peak_qpm": 0}
        now_ts = time.time()
        hour_ago = now_ts - 3600
        day_ago = now_ts - 86400
        last_hour = 0
        last_day = 0
        peak = 0
        per_minute = []
        for bucket_str, cnt in sorted(buckets.items()):
            try:
                bucket_ts = time.mktime(time.strptime(bucket_str, "%Y-%m-%d %H:%M"))
            except ValueError:
                continue
            if bucket_ts >= hour_ago:
                last_hour += cnt
            if bucket_ts >= day_ago:
                last_day += cnt
            if cnt > peak:
                peak = cnt
            if bucket_ts >= day_ago:
                per_minute.append({"bucket": bucket_str, "count": cnt})
        return {
            "per_minute": per_minute[-60:],
            "total_last_hour": last_hour,
            "total_last_day": last_day,
            "peak_qpm": peak,
        }

    def flush(self):
        with self._lock:
            self._persist()


_stats_store: "StatsStore | None" = None


def get_stats_store() -> StatsStore:
    global _stats_store
    if _stats_store is None:
        _stats_store = StatsStore()
    return _stats_store
