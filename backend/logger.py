import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from backend.config import LOG_DIR

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str = "filesearch") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    log_file = Path(LOG_DIR) / "filesearch.log"
    fh = RotatingFileHandler(
        str(log_file), maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    error_file = Path(LOG_DIR) / "errors.log"
    eh = RotatingFileHandler(
        str(error_file), maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    eh.setFormatter(formatter)
    eh.setLevel(logging.WARNING)
    logger.addHandler(eh)

    logger.propagate = False
    return logger


logger = get_logger()
