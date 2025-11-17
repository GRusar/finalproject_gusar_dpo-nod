"""Настройки проекта и Singleton для работы с конфигурацией."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"



class SingletonMeta(type):
    """Простой метакласс Singleton: один экземпляр на класс."""

    _instances: Dict[type, Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class SettingsLoader(metaclass=SingletonMeta):
    """Загружает конфиг из pyproject и предоставляет доступ через get()."""

    def __init__(self) -> None:
        if hasattr(self, "_config"):
            return
        self._config: Dict[str, Any] = {}
        self.reload()

    def get(self, key: str, default: Any = None) -> Any:
        """Вернуть значение настройки (если нет — default)."""
        return self._config.get(key, default)

    def reload(self) -> None:
        """Перечитывает pyproject и обновляет словарь настроек."""
        data = self._read_pyproject()
        valutatrade_section = data.get("tool", {}).get("valutatrade", {})
        if not valutatrade_section:
            raise RuntimeError("Секция [tool.valutatrade] отсутствует в pyproject.toml")

        config: Dict[str, Any] = {}
        for raw_key, value in valutatrade_section.items():
            key = raw_key.upper()
            if key.endswith("_FILE") or key.endswith("_DIR") or key.endswith("_PATH"):
                config[key] = (Path(value) if value else Path()).resolve()
            else:
                config[key] = value

        required_keys = [
            "DATA_DIR",
            "USERS_FILE",
            "PORTFOLIOS_FILE",
            "RATES_FILE",
            "RATES_TTL_SECONDS",
            "DEFAULT_BASE_CURRENCY",
            "LOG_PATH",
            "PARSER_LOG_PATH",
        ]
        missing = [key for key in required_keys if key not in config]
        if missing:
            missing_str = ", ".join(missing)
            raise RuntimeError(f"В конфигурации отсутствуют ключи: {missing_str}")

        self._config = config

    def _read_pyproject(self) -> Dict[str, Any]:
        if not PYPROJECT_PATH.exists():
            return {}
        with PYPROJECT_PATH.open("rb") as file:
            return tomllib.load(file)
