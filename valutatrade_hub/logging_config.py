"""Настройка логгера для доменных операций."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from valutatrade_hub.infra.settings import SettingsLoader

_LOGGER: Optional[logging.Logger] = None
LOGGER_NAME = "valutatrade.actions"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3
DEFAULT_LEVEL = logging.INFO


def _ensure_log_path(path: Path) -> Path:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_action_logger() -> logging.Logger:
    """Вернуть настроенный логгер, создавая его один раз."""
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    settings = SettingsLoader()
    log_path = Path(settings.get("LOG_PATH"))
    log_file = _ensure_log_path(log_path)

    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        logger.setLevel(DEFAULT_LEVEL)
        handler = RotatingFileHandler(
            log_file,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    _LOGGER = logger
    return logger
