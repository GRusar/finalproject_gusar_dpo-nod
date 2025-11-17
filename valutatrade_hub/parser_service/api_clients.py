"""Клиенты обращения к внешним API (CoinGecko, ExchangeRate-API)."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig, parser_config


class BaseApiClient(ABC):
    """Базовый интерфейс клиента получения курсов."""

    source_name: str

    def __init__(self, config: ParserConfig, source_name: str) -> None:
        self.config = config
        self.source_name = source_name

    @abstractmethod
    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        """Загрузить курсы: {"PAIR": {"rate": float, "meta": {...}}}."""


class CoinGeckoClient(BaseApiClient):
    """Загружает курсы криптовалют из CoinGecko."""

    def __init__(self, config: ParserConfig) -> None:
        super().__init__(config, source_name="coingecko")

    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        params = {
            "ids": ",".join(
                self.config.CRYPTO_ID_MAP[c] for c in self.config.CRYPTO_CURRENCIES
            ),
            "vs_currencies": self.config.BASE_CURRENCY.lower(),
        }
        start = time.perf_counter()
        try:
            response = requests.get(
                self.config.COINGECKO_URL,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ApiRequestError(
                f"CoinGecko запрос завершился ошибкой: {exc}",
            ) from exc

        elapsed_ms = (time.perf_counter() - start) * 1000
        data = response.json()
        rates: Dict[str, Dict[str, Any]] = {}
        for code in self.config.CRYPTO_CURRENCIES:
            coin_id = self.config.CRYPTO_ID_MAP[code]
            price_entry = data.get(coin_id, {})
            price = price_entry.get(self.config.BASE_CURRENCY.lower())
            if price is None:
                continue
            rates[f"{code}_{self.config.BASE_CURRENCY}"] = {
                "rate": float(price),
                "meta": {
                    "raw_id": coin_id,
                    "request_ms": round(elapsed_ms, 2),
                    "status_code": response.status_code,
                    "etag": response.headers.get("ETag"),
                    "api_timestamp": None,
                },
            }
        if not rates:
            raise ApiRequestError("CoinGecko вернул пустой набор курсов")
        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Загружает курсы фиатных валют из ExchangeRate-API."""

    def __init__(self, config: ParserConfig) -> None:
        super().__init__(config, source_name="exchangerate-api")

    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/latest/"
            f"{self.config.BASE_CURRENCY}"
        )
        start = time.perf_counter()
        try:
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ApiRequestError(
                "Запрос к ExchangeRate-API завершился ошибкой",
            ) from exc

        payload = response.json()
        if payload.get("result") != "success":
            raise ApiRequestError(
                f"ExchangeRate-API вернул ошибку: {payload.get('error-type')}",
            )
        elapsed_ms = (time.perf_counter() - start) * 1000
        api_timestamp = payload.get("time_last_update_utc")
        rates: Dict[str, Dict[str, Any]] = {}
        for code in self.config.FIAT_CURRENCIES:
            rate = payload.get("rates", {}).get(code)
            if rate is None:
                continue
            rates[f"{code}_{self.config.BASE_CURRENCY}"] = {
                "rate": float(rate),
                "meta": {
                    "raw_id": code,
                    "request_ms": round(elapsed_ms, 2),
                    "status_code": response.status_code,
                    "etag": response.headers.get("ETag"),
                    "api_timestamp": api_timestamp,
                },
            }
        if not rates:
            raise ApiRequestError("ExchangeRate-API не вернул ни одного курса")
        return rates


coin_gecko_client = CoinGeckoClient(parser_config)
exchange_rate_client = ExchangeRateApiClient(parser_config)
