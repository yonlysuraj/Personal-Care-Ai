"""Centralized logging setup with dated log files under logs/."""

from datetime import datetime
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
_CONFIGURED: set[str] = set()


def get_logger(name: str, app_name: str = "app") -> logging.Logger:
	"""Return a logger that writes to logs/{app_name}-YYYY-MM-DD.log."""
	logger = logging.getLogger(name)
	if name in _CONFIGURED:
		return logger

	LOG_DIR.mkdir(parents=True, exist_ok=True)
	date_stamp = datetime.now().strftime("%Y-%m-%d")
	log_file = LOG_DIR / f"{app_name}-{date_stamp}.log"

	formatter = logging.Formatter(
		"%(asctime)s | %(levelname)s | %(name)s | %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S",
	)

	file_handler = logging.FileHandler(log_file, encoding="utf-8")
	file_handler.setFormatter(formatter)

	logger.setLevel(logging.INFO)
	logger.addHandler(file_handler)
	logger.propagate = False

	_CONFIGURED.add(name)
	return logger
