"""Centralized logging setup with dated log files under logs/."""

from datetime import datetime
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
_CONFIGURED: set[str] = set()


def silence_console_logging(logger_names: list[str] | None = None) -> None:
	"""Remove stream handlers from selected loggers to reduce terminal log noise."""
	names = logger_names or [""]
	for name in names:
		logger = logging.getLogger(name)
		stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
		for handler in stream_handlers:
			logger.removeHandler(handler)


def get_logger(name: str, app_name: str = "app") -> logging.Logger:
	"""Return a logger that writes to logs/{app_name}/{app_name}-YYYY-MM-DD.log."""
	logger = logging.getLogger(name)
	if name in _CONFIGURED:
		return logger

	app_log_dir = LOG_DIR / app_name
	app_log_dir.mkdir(parents=True, exist_ok=True)
	date_stamp = datetime.now().strftime("%Y-%m-%d")
	log_file = app_log_dir / f"{app_name}-{date_stamp}.log"

	formatter = logging.Formatter(
		"%(asctime)s | %(levelname)s | %(name)s | pid=%(process)d tid=%(thread)d | %(filename)s:%(lineno)d | %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S",
	)

	file_handler = logging.FileHandler(log_file, encoding="utf-8")
	file_handler.setFormatter(formatter)

	logger.setLevel(logging.INFO)
	logger.addHandler(file_handler)
	logger.propagate = False

	_CONFIGURED.add(name)
	return logger
