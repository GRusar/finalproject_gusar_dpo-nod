"""Хранилище для результатов работы Parser Service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from valutatrade_hub.parser_service.config import parser_config


class RatesStorage:
    """Читает и записывает кеш курсов и историю обновлений."""

    def __init__(
        self,
        rates_path: Path | None = None,
        history_path: Path | None = None,
    ) -> None:
        self.rates_path = Path(rates_path or parser_config.RATES_FILE_PATH)
        self.history_path = Path(history_path or parser_config.HISTORY_FILE_PATH)

    def read_rates(self) -> Dict[str, Any]:
        if not self.rates_path.exists():
            return {"pairs": {}, "last_refresh": None}
        with self.rates_path.open("r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {"pairs": {}, "last_refresh": None}

    def write_rates(self, data: Dict[str, Any]) -> None:
        self._atomic_write(self.rates_path, data)

    def append_history(self, records: list[Dict[str, Any]]) -> None:
        history = self._read_history()
        history.extend(records)
        self._atomic_write(self.history_path, history)

    def _read_history(self) -> list[Dict[str, Any]]:
        if not self.history_path.exists():
            return []
        with self.history_path.open("r", encoding="utf-8") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                return []
        if isinstance(data, list):
            return data
        return []

    def _atomic_write(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        tmp_path.replace(path)


rates_storage = RatesStorage()
