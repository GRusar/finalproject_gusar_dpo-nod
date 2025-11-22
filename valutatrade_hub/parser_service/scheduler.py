"""Простой планировщик для периодического обновления курсов."""

from __future__ import annotations

import time
from typing import Iterable

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import get_parser_logger
from valutatrade_hub.parser_service.api_clients import (
    coin_gecko_client,
    exchange_rate_client,
)
from valutatrade_hub.parser_service.updater import RatesUpdater

logger = get_parser_logger().getChild("scheduler")


def run_scheduler(
    interval_seconds: int = 300,
    active_sources: Iterable[str] | None = None,
    updater: RatesUpdater | None = None,
) -> None:
    """Запускает циклическое обновление курсов с задержкой interval_seconds."""
    clients = {
        "coingecko": coin_gecko_client,
        "exchangerate": exchange_rate_client,
        "exchangerate-api": exchange_rate_client,
    }
    selected_clients= (
        [clients[name] for name in active_sources]
        if active_sources
        else clients.values()
    )
    updater = updater or RatesUpdater(selected_clients)
    logger.info(
        "Scheduler started: interval=%s seconds, sources=%s",
        interval_seconds,
        list(active_sources) if active_sources else "all",
    )

    try:
        while True:
            start = time.perf_counter()
            try:
                result = updater.run_update(active_sources=active_sources)
                logger.info(
                    "Update OK: total_rates=%s, last_refresh=%s, errors=%s",
                    result.get("total_rates"),
                    result.get("last_refresh"),
                    result.get("errors"),
                )
                print(
                    f"[scheduler] OK: total_rates={result.get('total_rates')} "
                    f"last_refresh={result.get('last_refresh')} "
                    f"errors={result.get('errors')}",
                )
            except ApiRequestError as exc:
                logger.error("Update failed: %s", exc)
                print(f"[scheduler] Failed: {exc}")
            except Exception as exc:
                logger.exception("Unexpected error in scheduler: %s", exc)
                print(f"[scheduler] Unexpected error: {exc}")
            elapsed = time.perf_counter() - start
            sleep_time = max(0, interval_seconds - int(elapsed))
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user (KeyboardInterrupt)")
        print("Планировщик остановлен.")
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    from valutatrade_hub.parser_service.api_clients import (
        coin_gecko_client,
        exchange_rate_client,
    )

    updater = RatesUpdater([coin_gecko_client, exchange_rate_client])
    run_scheduler(updater)
