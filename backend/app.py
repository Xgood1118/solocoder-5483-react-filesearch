import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory, abort, Response
from flask_cors import CORS

from backend.config import CORS_ORIGIN, FLASK_DEBUG, FLASK_PORT, FILES_ROOT_DIR
from backend.index.manager import get_index_manager
from backend.logger import logger
from backend.search.highlighter import escape_html_full
from backend.search.service import SearchOptions, search
from backend.stats.store import get_stats_store
from backend.extract.text_extractor import read_text


def _relative_path(abs_path: str) -> str:
    """Strip FILES_ROOT_DIR prefix and normalize to forward-slash relative path.

    If ``abs_path`` is outside FILES_ROOT_DIR (shouldn't happen in normal operation),
    return the original absolute path so downstream handlers (file_content /
    file_detail) still have what they need to open the file.
    """
    if not abs_path:
        return abs_path
    try:
        root = Path(FILES_ROOT_DIR).resolve()
        p = Path(abs_path).resolve()
        rel = p.relative_to(root)
        return rel.as_posix()
    except (ValueError, OSError):
        return abs_path


_update_lock = threading.Lock()


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": CORS_ORIGIN, "supports_credentials": True}})

    im = get_index_manager()
    stats = get_stats_store()

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "ts": time.time()})

    @app.route("/api/search", methods=["GET"])
    def api_search():
        q = request.args.get("q", "").strip()
        if not q:
            return jsonify({"results": [], "cursor": None, "total_returned": 0, "error": "q required"})

        # Validate page + page_size; reject obviously invalid values instead of
        # silently clamping them. This stops callers from spamming empty pages
        # or skipping ahead via negative indices.
        try:
            page = int(request.args.get("page", "1"))
        except ValueError:
            return jsonify({"results": [], "cursor": None, "total_returned": 0, "error": "page must be integer"})
        if page < 1:
            return jsonify({"results": [], "cursor": None, "total_returned": 0, "error": "page must be >= 1"})

        try:
            page_size = int(request.args.get("page_size", "20"))
        except ValueError:
            return jsonify({"results": [], "cursor": None, "total_returned": 0, "error": "page_size must be integer"})
        if page_size < 1:
            return jsonify({"results": [], "cursor": None, "total_returned": 0, "error": "page_size must be >= 1"})

        opts = SearchOptions(q=q, page=page, page_size=page_size)
        opts.path_prefix = request.args.get("path_prefix", "")
        opts.mime = request.args.get("mime", "")
        opts.cursor = request.args.get("cursor") or None
        for key in ("from_date", "to_date"):
            val = request.args.get(key)
            if val:
                ts: Optional[float] = None
                try:
                    ts = float(val)
                except ValueError:
                    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
                        try:
                            ts = datetime.strptime(val, fmt).timestamp()
                            break
                        except ValueError:
                            continue
                if ts is None:
                    return jsonify({
                        "results": [], "cursor": None, "total_returned": 0,
                        "error": f"{key} must be ISO date or epoch seconds",
                    })
                setattr(opts, key, ts)

        result = search(opts)
        file_ids = [r["file_id"] for r in result["results"]]
        try:
            stats.record_search(q, file_ids)
        except Exception as e:
            logger.warning(f"record stats failed: {e}")

        # Strip FILES_ROOT_DIR prefix from each result's path so we don't leak
        # the deployment host's directory structure (was exposing
        # C:\Users\白东鑫\work01\... in the UI).
        for r in result.get("results", []):
            if r.get("path"):
                r["path"] = _relative_path(r["path"])

        return jsonify(result)

    @app.route("/api/files/<file_id>", methods=["GET"])
    def api_file_detail(file_id: str):
        doc = im.find_by_id(file_id)
        if doc is None:
            abort(404)
        return jsonify({
            "file_id": doc.get("file_id"),
            "path": _relative_path(doc.get("path", "")),
            "name": doc.get("name"),
            "size": doc.get("size"),
            "mtime": doc.get("mtime"),
            "mime_type": doc.get("mime_type"),
            "owner": doc.get("owner"),
            "tags": [t for t in (doc.get("tags") or "").split(",") if t],
            "ext": doc.get("ext"),
            "ocr_low_conf": bool(doc.get("ocr_low_conf")),
            "content_preview": doc.get("content_stored") or "",
            "parent_dir": _relative_path(doc.get("parent_dir", "")),
        })

    @app.route("/api/files/<file_id>/related", methods=["GET"])
    def api_file_related(file_id: str):
        doc = im.find_by_id(file_id)
        if doc is None:
            abort(404)
        per = 5
        try:
            per = int(request.args.get("per", "5"))
        except ValueError:
            pass
        related = im.related_files(doc, per_dim=per)
        for key in related:
            for d in related[key]:
                d.pop("content_stored", None)
                d.pop("code_index", None)
                d["tags"] = [t for t in (d.get("tags") or "").split(",") if t]
                if d.get("path"):
                    d["path"] = _relative_path(d["path"])
                if d.get("parent_dir"):
                    d["parent_dir"] = _relative_path(d["parent_dir"])
        return jsonify(related)

    @app.route("/api/files/<file_id>/content", methods=["GET"])
    def api_file_content(file_id: str):
        doc = im.find_by_id(file_id)
        if doc is None:
            abort(404)
        path = Path(doc.get("path", ""))
        if not path.exists() or not path.is_file():
            abort(404)
        mime = doc.get("mime_type") or "application/octet-stream"
        if mime == "application/pdf" or mime.startswith("image/"):
            return send_from_directory(str(path.parent), path.name, mimetype=mime, as_attachment=False)
        if mime.startswith("text/") or mime == "application/json":
            text = read_text(path, max_len=500_000) or ""
            if request.args.get("html"):
                safe = escape_html_full(text)
                return Response(f"<pre>{safe}</pre>", mimetype="text/html")
            return Response(text, mimetype="text/plain")
        return send_from_directory(str(path.parent), path.name, mimetype=mime, as_attachment=True)

    @app.route("/api/stats/top-terms", methods=["GET"])
    def api_top_terms():
        k = 20
        try:
            k = int(request.args.get("k", "20"))
        except ValueError:
            pass
        return jsonify({"items": stats.top_terms(k)})

    @app.route("/api/stats/top-files", methods=["GET"])
    def api_top_files():
        k = 20
        try:
            k = int(request.args.get("k", "20"))
        except ValueError:
            pass
        label_map = {}
        with im.ix.searcher() as s:
            for d in s.all_stored_fields():
                label_map[d.get("file_id", "")] = d.get("name", d.get("path", ""))
        return jsonify({"items": stats.top_files(label_map, k)})

    @app.route("/api/stats/qps", methods=["GET"])
    def api_qps():
        return jsonify(stats.qps_summary())

    @app.route("/api/index/status", methods=["GET"])
    def api_index_status():
        return jsonify(im.get_stats())

    @app.route("/api/index/rebuild", methods=["POST"])
    def api_index_rebuild():
        if _update_lock.locked():
            return jsonify({"ok": False, "msg": "already running"}), 409

        def _run():
            with _update_lock:
                try:
                    im.run_incremental_update()
                    stats.flush()
                except Exception as e:
                    logger.exception(f"background index update failed: {e}")

        threading.Thread(target=_run, daemon=True).start()
        return jsonify({"ok": True, "msg": "started"})

    return app
