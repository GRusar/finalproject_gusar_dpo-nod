"""Настройки проекта и Singleton для работы с конфигурацией."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
ENV_PYPROJECT_PATH = "VALUTATRADE_PYPROJECT_PATH"


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
        if data and not valutatrade_section:
            raise RuntimeError("Секция [tool.valutatrade] отсутствует в pyproject.toml")

        config: Dict[str, Any] = {}
        for raw_key, value in valutatrade_section.items():
            key = raw_key.upper()
            if key.endswith("_FILE") or key.endswith("_DIR") or key.endswith("_PATH"):
                if value is None:
                    config[key] = PROJECT_ROOT
                    continue
                path_value = Path(value)
                if not path_value.is_absolute():
                    path_value = PROJECT_ROOT / path_value
                config[key] = path_value.resolve()
            else:
                config[key] = value

        required_keys = [
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
        """
        Читает pyproject.toml из:
        - корня проекта
        - текущей директории
        - пути из переменной окружения VALUTATRADE_PYPROJECT_PATH
        """
        candidates = [
            PYPROJECT_PATH,
            Path.cwd() / "pyproject.toml",
        ]
        env_override = os.getenv(ENV_PYPROJECT_PATH)
        if env_override:
            candidates.append(Path(env_override).expanduser())

        target_path = next((path for path in candidates if path.exists()), None)
        if target_path is None:
            raise RuntimeError(
                "pyproject.toml не найден. ",
                "Укажите путь через VALUTATRADE_PYPROJECT_PATH",
            )

        with target_path.open("rb") as file:
            return tomllib.load(file)
