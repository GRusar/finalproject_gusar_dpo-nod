"""Простая обёртка над json-хранилищем с общим интерфейсом."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from valutatrade_hub.infra.settings import SingletonMeta, settings


class DatabaseManager(metaclass=SingletonMeta):
    """Singleton для работы с users.json, portfolios.json и rates.json."""

    def __init__(self) -> None:
        if hasattr(self, "_paths"):
            return
        self._paths: Dict[str, Path] = {
            "users": Path(settings.get("USERS_FILE")),
            "portfolios": Path(settings.get("PORTFOLIOS_FILE")),
            "rates": Path(settings.get("RATES_FILE")),
        }

    def read(self, name: str, default: Any) -> Any:
        """Прочитать файл по ключу (users/portfolios/rates)."""
        path = self._get_path(name)
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return default

    def write(self, name: str, data: Any) -> None:
        """Сохранить данные в json-файл по ключу."""
        path = self._get_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def _get_path(self, name: str) -> Path:
        try:
            return self._paths[name]
        except KeyError as exc:
            raise ValueError(f"Неизвестный ключ базы данных '{name}'") from exc
