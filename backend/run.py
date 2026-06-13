import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app import create_app
from backend.config import FLASK_PORT, FLASK_DEBUG
from backend.index.manager import get_index_manager
from backend.logger import logger
import threading


if __name__ == "__main__":
    app = create_app()
    im = get_index_manager()
    t = threading.Thread(target=im.run_incremental_update, daemon=True)
    t.start()
    logger.info(f"starting Flask on :{FLASK_PORT} debug={FLASK_DEBUG}")
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG, use_reloader=False, threaded=True)
