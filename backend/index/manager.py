import hashlib
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

from whoosh import index as whoosh_index
from whoosh.index import Index
from whoosh.writing import IndexWriter, AsyncWriter

from backend.config import FILES_ROOT_DIR, INDEX_DIR
from backend.extract.dispatcher import dispatch
from backend.extract.ocr_extractor import ocr_queue
from backend.index.schema import make_schema
from backend.logger import logger
from backend.mime_utils import guess_mime


def _file_id(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8")).hexdigest()[:24]


@dataclass
class IndexStats:
    total_files: int = 0
    indexed: int = 0
    failed: int = 0
    deleted: int = 0
    skipped: int = 0
    last_update: float = 0.0
    in_progress: bool = False
    failures: List[Dict[str, str]] = field(default_factory=list)


class IndexManager:
    def __init__(self, index_dir: Path = INDEX_DIR, root_dir: Path = FILES_ROOT_DIR):
        self.index_dir = Path(index_dir)
        self.root_dir = Path(root_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._index: Optional[Index] = None
        self._stats = IndexStats()
        self._load_or_create()
        ocr_queue.set_callback(self._on_ocr_done)

    def _load_or_create(self):
        schema = make_schema()
        idx_path = self.index_dir
        if idx_path.exists() and list(idx_path.glob("*.seg")):
            try:
                self._index = whoosh_index.open_dir(str(idx_path))
                logger.info(f"opened existing index at {idx_path}")
                return
            except Exception as e:
                logger.warning(f"open index failed, recreating: {e}")
        self._index = whoosh_index.create_in(str(idx_path), schema)
        logger.info(f"created new index at {idx_path}")

    @property
    def ix(self) -> Index:
        return self._index

    def get_stats(self) -> Dict:
        with self._lock:
            stats = self._stats
            doc_count = 0
            if self._index:
                try:
                    with self._index.reader() as r:
                        doc_count = r.doc_count() - r.deleted_count()
                except Exception:
                    doc_count = self._index.doc_count()
            return {
                "total_files_scanned": stats.total_files,
                "indexed_count": doc_count,
                "failed_count": stats.failed,
                "deleted_count": stats.deleted,
                "skipped_count": stats.skipped,
                "last_update_ts": stats.last_update,
                "last_update": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stats.last_update)) if stats.last_update else None,
                "in_progress": stats.in_progress,
                "recent_failures": stats.failures[-20:],
                "index_dir": str(self.index_dir),
                "root_dir": str(self.root_dir),
            }

    def _iter_all_files(self) -> Iterator[Path]:
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            for fn in filenames:
                yield Path(dirpath) / fn

    def _snapshot_mtime(self) -> Dict[str, Tuple[float, int]]:
        result: Dict[str, Tuple[float, int]] = {}
        for p in self._iter_all_files():
            try:
                st = p.stat()
                result[str(p.resolve())] = (st.st_mtime, st.st_size)
            except OSError:
                continue
        return result

    def _existing_doc_mtimes(self) -> Dict[str, Tuple[float, str]]:
        result: Dict[str, Tuple[float, str]] = {}
        with self._index.searcher() as s:
            for doc in s.all_stored_fields():
                p = doc.get("path")
                mt = doc.get("mtime", 0.0)
                fid = doc.get("file_id", "")
                if p:
                    result[p] = (float(mt), fid)
        return result

    def _add_failure(self, path: str, error: str):
        with self._lock:
            self._stats.failed += 1
            self._stats.failures.append({"path": path, "error": error, "ts": time.time()})
            if len(self._stats.failures) > 500:
                self._stats.failures = self._stats.failures[-500:]

    def _build_doc(self, file_path: Path, mtime: float, size: int) -> Optional[Dict]:
        mime = guess_mime(file_path)
        result = dispatch(file_path, mime)
        if not result.success and not result.content:
            self._add_failure(str(file_path), result.error or "extract failed")
            if result.ocr_confidence_low:
                pass
            else:
                return None

        try:
            owner = file_path.owner()
        except Exception:
            owner = "unknown"

        tags = self._infer_tags(file_path, mime)
        ext = file_path.suffix.lower().lstrip(".")
        parent_dir = str(file_path.parent.resolve())

        return {
            "file_id": _file_id(str(file_path.resolve())),
            "path": str(file_path.resolve()),
            "name": file_path.name,
            "content": result.content or "",
            "content_stored": (result.content or "")[:20000],
            "size": size,
            "mtime": mtime,
            "mime_type": mime,
            "owner": owner,
            "tags": ",".join(tags),
            "code_index": result.metadata.get("code_index", ""),
            "ocr_low_conf": result.ocr_confidence_low,
            "ext": ext,
            "parent_dir": parent_dir,
        }

    def _infer_tags(self, file_path: Path, mime: str) -> List[str]:
        tags: List[str] = []
        name = file_path.name
        parent_name = file_path.parent.name
        haystack = f"{name} {parent_name}"

        kw_map = {
            "合同": "法律",
            "协议": "法律",
            "保密": "法律",
            "竞业": "法律",
            "NDA": "法律",
            "nda": "法律",
            "法务": "法律",
            "法律": "法律",
            "律师": "法律",
            "设计稿": "设计",
            "设计": "设计",
            "UI": "设计",
            "ui": "设计",
            "UX": "设计",
            "ux": "设计",
            "Figma": "设计",
            "figma": "设计",
            "财务": "财务",
            "报表": "财务",
            "预算": "财务",
            "发票": "财务",
            "审计": "财务",
            "会议纪要": "会议",
            "评审": "会议",
            "周报": "会议",
            "月报": "会议",
            "简历": "人事",
            "招聘": "人事",
            "offer": "人事",
            "Offer": "人事",
            "劳动合同": "人事",
            "代码": "技术",
            "技术方案": "技术",
            "架构": "技术",
            "API": "技术",
            "api": "技术",
        }

        direct_tags = [
            "合同", "协议", "保密", "竞业", "法律", "法务", "律师",
            "设计稿", "设计", "财务", "报表", "预算", "发票", "审计",
            "会议纪要", "评审", "周报", "月报", "简历", "招聘",
            "技术方案", "架构", "代码",
        ]

        for kw in direct_tags:
            if kw in haystack:
                if kw not in tags:
                    tags.append(kw)

        for kw, tag in kw_map.items():
            if kw in haystack and tag not in tags:
                tags.append(tag)

        return tags

    def run_incremental_update(self, limit: Optional[int] = None) -> Dict:
        with self._lock:
            if self._stats.in_progress:
                return {"ok": False, "msg": "already in progress"}
            self._stats.in_progress = True

        try:
            return self._do_update(limit=limit)
        finally:
            with self._lock:
                self._stats.in_progress = False
                self._stats.last_update = time.time()

    def _do_update(self, limit: Optional[int]) -> Dict:
        logger.info("start incremental index update")
        snapshot = self._snapshot_mtime()
        existing = self._existing_doc_mtimes()

        existing_paths: Set[str] = set(existing.keys())
        current_paths: Set[str] = set(snapshot.keys())

        to_delete_paths = existing_paths - current_paths
        to_delete_file_ids: List[str] = []
        for p in to_delete_paths:
            _mt, fid = existing[p]
            if fid:
                to_delete_file_ids.append(fid)
        to_update: List[str] = []
        for p in current_paths:
            if p not in existing:
                to_update.append(p)
            else:
                mtime_new, _ = snapshot[p]
                mtime_old, _fid = existing[p]
                if mtime_new > mtime_old + 1e-3:
                    to_update.append(p)

        to_update_sorted = sorted(to_update, key=lambda p: snapshot[p][0], reverse=True)
        if limit and limit > 0:
            to_update_sorted = to_update_sorted[:limit]

        with self._lock:
            self._stats.total_files = len(snapshot)
            self._stats.skipped = len(current_paths) - len(to_update)

        writer = AsyncWriter(self._index, delay=0.25, writerargs={"limitmb": 256})
        added = 0
        updated = 0
        deleted = 0
        try:
            for path_str in to_update_sorted:
                p = Path(path_str)
                mtime, size = snapshot[path_str]
                try:
                    doc = self._build_doc(p, mtime, size)
                    if doc is None:
                        continue
                    writer.update_document(**doc)
                    added += 1
                    if added % 50 == 0:
                        logger.info(f"indexed {added}/{len(to_update_sorted)} files")
                except Exception as e:
                    logger.exception(f"index error for {p}: {e}")
                    self._add_failure(path_str, f"index: {e}")

            for fid in to_delete_file_ids:
                try:
                    writer.delete_by_term("file_id", fid)
                    deleted += 1
                except Exception as e:
                    logger.warning(f"delete from index failed file_id={fid}: {e}")

            writer.commit()
            try:
                if deleted > 0 or (added + updated) % 2000 == 0:
                    self._index.optimize()
                    logger.info(f"index optimized: deleted_cleaned={deleted}")
            except Exception as e:
                logger.warning(f"index optimize skipped: {e}")
        except Exception:
            try:
                writer.cancel()
            except Exception:
                pass
            raise

        with self._lock:
            self._stats.indexed = added
            self._stats.deleted += deleted

        logger.info(f"incremental done: added={added} updated={updated} deleted={deleted} failed={self._stats.failed}")
        return {"ok": True, "added": added, "updated": updated, "deleted": deleted, "failed": self._stats.failed, "scanned": len(snapshot)}

    def _on_ocr_done(self, file_path: str, page: Optional[int], text: str):
        if not text:
            return
        try:
            with self._index.searcher() as s:
                doc = None
                for hit in s.documents(path=file_path):
                    doc = dict(hit)
                    break
            if doc is None:
                return
            new_content = (doc.get("content_stored") or "") + "\n\n" + text
            doc["content"] = (doc.get("content") or "") + "\n\n" + text
            doc["content_stored"] = new_content[:20000]
            writer: IndexWriter = self._index.writer()
            try:
                writer.update_document(**doc)
                writer.commit()
                logger.info(f"OCR result merged into index for {file_path}")
            except Exception:
                writer.cancel()
                raise
        except Exception as e:
            logger.warning(f"apply OCR result failed for {file_path}: {e}")

    def find_by_path(self, path: str) -> Optional[Dict]:
        with self._index.searcher() as s:
            for hit in s.documents(path=path):
                return dict(hit)
        return None

    def find_by_id(self, file_id: str) -> Optional[Dict]:
        with self._index.searcher() as s:
            for hit in s.documents(file_id=file_id):
                return dict(hit)
        return None

    def related_files(self, doc: Dict, per_dim: int = 5) -> Dict[str, List[Dict]]:
        result: Dict[str, List[Dict]] = {"same_dir": [], "same_tags": [], "same_owner": []}
        parent = doc.get("parent_dir")
        tags = [t for t in (doc.get("tags") or "").split(",") if t]
        owner = doc.get("owner")
        self_path = doc.get("path")
        with self._index.searcher() as s:
            if parent:
                from whoosh.query import Term
                res = s.search(Term("parent_dir", parent), limit=per_dim + 5)
                for h in res:
                    d = dict(h)
                    if d.get("path") != self_path and len(result["same_dir"]) < per_dim:
                        result["same_dir"].append(d)
            if tags:
                from whoosh.query import Or
                terms = [Term("tags", t) for t in tags]
                res = s.search(Or(terms), limit=per_dim + 5)
                for h in res:
                    d = dict(h)
                    if d.get("path") != self_path and len(result["same_tags"]) < per_dim:
                        result["same_tags"].append(d)
            if owner:
                from whoosh.query import Term
                res = s.search(Term("owner", owner), sortedby=["mtime"], reverse=True, limit=per_dim + 5)
                for h in res:
                    d = dict(h)
                    if d.get("path") != self_path and len(result["same_owner"]) < per_dim:
                        result["same_owner"].append(d)
        return result


_index_manager: Optional[IndexManager] = None


def get_index_manager() -> IndexManager:
    global _index_manager
    if _index_manager is None:
        _index_manager = IndexManager()
    return _index_manager
