"""Клиенты обращения к внешним API (CoinGecko, ExchangeRate-API)."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import get_parser_logger
from valutatrade_hub.parser_service.config import ParserConfig, parser_config


class BaseApiClient(ABC):
    """Базовый интерфейс клиента получения курсов."""

    source_name: str

    def __init__(self, config: ParserConfig, source_name: str) -> None:
        self.config = config
        self.source_name = source_name
        self.logger = get_parser_logger().getChild(f"client.{self.source_name}")

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
        self.logger.info(
            "CoinGecko запрос: ids=%s, vs=%s",
            params["ids"],
            params["vs_currencies"],
        )
        try:
            response = requests.get(
                self.config.COINGECKO_URL,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            self.logger.error("CoinGecko ошибка: %s", exc)
            raise ApiRequestError(
                f"CoinGecko запрос завершился ошибкой: {exc}",
            ) from exc

        elapsed_ms = (time.perf_counter() - start) * 1000
        self.logger.info(
            "CoinGecko ответ %s за %.2f мс",
            response.status_code,
            elapsed_ms,
        )
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
            self.logger.error("CoinGecko вернул пустой набор курсов")
            raise ApiRequestError("CoinGecko вернул пустой набор курсов")
        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Загружает курсы фиатных валют из ExchangeRate-API."""

    def __init__(self, config: ParserConfig) -> None:
        super().__init__(config, source_name="exchangerate")

    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        api_key = self.config.exchange_api_key
        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{api_key}/latest/"
            f"{self.config.BASE_CURRENCY}"
        )
        start = time.perf_counter()
        self.logger.info("ExchangeRate запрос: %s", url)
        try:
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as exc:
            detail = getattr(exc.response, "text", str(exc))
            self.logger.error(
                "ExchangeRate HTTP ошибка: %s (detail=%s)",
                exc,
                detail,
            )
            raise ApiRequestError(
                f"ExchangeRate-API: {detail}",
            ) from exc

        payload = response.json()
        if payload.get("result") != "success":
            self.logger.error("ExchangeRate-API ответил ошибкой: %s", payload)
            raise ApiRequestError(
                f"ExchangeRate-API вернул ошибку: {payload.get('error-type')} "
                f"({payload})",
            )
        elapsed_ms = (time.perf_counter() - start) * 1000
        api_timestamp = payload.get("time_last_update_utc")
        rates: Dict[str, Dict[str, Any]] = {}
        for code in self.config.FIAT_CURRENCIES:
            base_to_code = payload.get("conversion_rates", {}).get(code)
            if base_to_code is None or base_to_code == 0:
                continue
            rates[f"{code}_{self.config.BASE_CURRENCY}"] = {
                # API отдаёт курс BASE→CODE, для CODE→BASE инвертируем
                "rate": float(1 / base_to_code),
                "meta": {
                    "raw_id": code,
                    "request_ms": round(elapsed_ms, 2),
                    "status_code": response.status_code,
                    "etag": response.headers.get("ETag"),
                    "api_timestamp": api_timestamp,
                },
            }
        if not rates:
            self.logger.error(
                "ExchangeRate-API не вернул ни одного курса. payload=%s",
                payload,
            )
            raise ApiRequestError(
                "ExchangeRate-API не вернул ни одного курса"
                f"raw api payload: \n{payload}",
            )
        return rates


coin_gecko_client = CoinGeckoClient(parser_config)
exchange_rate_client = ExchangeRateApiClient(parser_config)
