import threading
import queue
from pathlib import Path
from typing import Dict, List, Optional, Callable

from backend.config import OCR_ENABLED, OCR_LANG, OCR_QUEUE_MAX
from backend.logger import logger


class OCRTask:
    def __init__(self, file_path: str | Path, page: Optional[int] = None):
        self.file_path = str(file_path)
        self.page = page
        self.result: Optional[str] = None
        self.error: Optional[str] = None
        self.done = threading.Event()


class OCRQueue:
    def __init__(self):
        self._q: "queue.Queue[OCRTask]" = queue.Queue(maxsize=OCR_QUEUE_MAX)
        self._workers: List[threading.Thread] = []
        self._lock = threading.Lock()
        self._started = False
        self._ocr_results: Dict[str, Dict[int, str]] = {}
        self._on_done_cb: Optional[Callable[[str, Optional[int], str], None]] = None

    def set_callback(self, cb: Callable[[str, Optional[int], str], None]):
        self._on_done_cb = cb

    def start(self, workers: int = 2):
        with self._lock:
            if self._started:
                return
            self._started = True
            for _ in range(workers):
                t = threading.Thread(target=self._run, daemon=True)
                t.start()
                self._workers.append(t)

    def submit(self, task: OCRTask) -> bool:
        if not OCR_ENABLED:
            return False
        self.start()
        try:
            self._q.put_nowait(task)
            return True
        except queue.Full:
            logger.warning("OCR queue full, dropping task")
            return False

    def get_cached(self, file_path: str) -> Dict[int, str]:
        return self._ocr_results.get(file_path, {})

    def _run(self):
        try:
            from PIL import Image
            import pytesseract
        except ImportError:
            logger.error("OCR deps not available (Pillow/pytesseract)")
            return

        while True:
            task = self._q.get()
            if task is None:
                break
            try:
                img = Image.open(task.file_path)
                text = pytesseract.image_to_string(img, lang=OCR_LANG)
                task.result = text or ""
                key = task.file_path
                page = task.page or 0
                self._ocr_results.setdefault(key, {})[page] = task.result
                if self._on_done_cb:
                    try:
                        self._on_done_cb(key, task.page, task.result)
                    except Exception as cb_e:
                        logger.warning(f"OCR callback error: {cb_e}")
            except Exception as e:
                task.error = str(e)
                logger.warning(f"OCR failed {task.file_path}: {e}")
            finally:
                task.done.set()
                self._q.task_done()


ocr_queue = OCRQueue()
