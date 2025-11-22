"""Сбор и обновление курсов из внешних API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.utils import parse_iso_datetime
from valutatrade_hub.logging_config import get_parser_logger
from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.storage import RatesStorage, rates_storage

logger = get_parser_logger().getChild("updater")

class RatesUpdater:
    """Оркестрирует опрос клиентов и запись данных в хранилище."""

    SOURCE_ALIASES = {
        "exchangerate-api": "exchangerate",
    }

    @classmethod
    def _normalize_source(cls, name: str) -> str:
        return cls.SOURCE_ALIASES.get(name.lower(), name.lower())

    def __init__(
        self,
        clients: Iterable[BaseApiClient],
        storage: RatesStorage | None = None,
    ) -> None:
        self.clients = list(clients)
        self.storage = storage or rates_storage

    def run_update(self, active_sources: Iterable[str] | None = None) -> Dict[str, Any]:
        sources = (
            {self._normalize_source(name) for name in active_sources}
            if active_sources
            else None
        )
        new_entries: Dict[str, Dict[str, Any]] = {}
        history_records: List[Dict[str, Any]] = []
        errors: List[str] = []
        total_rates = 0

        logger.info("Starting rates update...")
        for client in self.clients:
            source_name = self._normalize_source(
                getattr(
                    client,
                    "source_name",
                    client.__class__.__name__,
                ),
            )
            if sources and source_name not in sources:
                logger.info("Пропускаем источник %s (не выбран)", source_name)
                continue
            logger.info("Fetching from %s...", source_name)
            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                message = f"Failed to fetch from {source_name}: {error}"
                logger.error(message)
                errors.append(message)
                continue
            updated_at = datetime.now(timezone.utc).isoformat()
            for pair, payload in rates.items():
                rate = float(payload.get("rate"))
                entry = {
                    "rate": rate,
                    "updated_at": updated_at,
                    "source": client.source_name,
                }
                meta = payload.get("meta", {})
                new_entries[pair] = entry
                from_code, to_code = pair.split("_", 1)
                history_records.append(
                    {
                        "id": f"{pair}_{updated_at}",
                        "from_currency": from_code,
                        "to_currency": to_code,
                        "rate": rate,
                        "timestamp": meta.get("api_timestamp") or updated_at,
                        "source": client.source_name,
                        "meta": meta,
                    },
                )
            count = len(rates)
            total_rates += count
            logger.info("%s: OK (%d rates)", source_name, count)

        if not new_entries:
            raise ApiRequestError("Не удалось получить данные ни от одного источника")

        current_data = self.storage.read_rates()
        existing_pairs = current_data.get("pairs", {})

        def is_newer(new_entry: Dict[str, Any], old_entry: Dict[str, Any]) -> bool:
            new_ts = parse_iso_datetime(new_entry.get("updated_at"))
            old_ts = parse_iso_datetime(old_entry.get("updated_at"))
            if new_ts is None:
                return False
            if old_ts is None:
                return True
            return new_ts > old_ts

        for pair, entry in new_entries.items():
            old_entry = existing_pairs.get(pair)
            if not old_entry or is_newer(entry, old_entry):
                existing_pairs[pair] = entry

        payload = {
            "pairs": existing_pairs,
            "last_refresh": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            "Writing %d rates to %s",
            len(existing_pairs),
            self.storage.rates_path,
        )
        self.storage.write_rates(payload)

        if history_records:
            self.storage.append_history(history_records)

        logger.info("Update finished: %d rates", total_rates)
        if errors:
            logger.warning("Completed with errors: %s", " | ".join(errors))
        return {
            "total_rates": total_rates,
            "errors": errors,
            "last_refresh": payload["last_refresh"],
        }
