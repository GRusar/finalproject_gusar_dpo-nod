"""Клиенты обращения к внешним API (CoinGecko, ExchangeRate-API)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig, parser_config


class BaseApiClient(ABC):
    """Базовый интерфейс клиента получения курсов."""

    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """Загрузить курсы и вернуть словарь вида {"PAIR": rate}."""


class CoinGeckoClient(BaseApiClient):
    """Загружает курсы криптовалют из CoinGecko."""

    def fetch_rates(self) -> Dict[str, float]:
        params = {
            "ids": ",".join(
                self.config.CRYPTO_ID_MAP[c] for c in self.config.CRYPTO_CURRENCIES
            ),
            "vs_currencies": self.config.BASE_CURRENCY.lower(),
        }
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

        data = response.json()
        rates: Dict[str, float] = {}
        for code in self.config.CRYPTO_CURRENCIES:
            coin_id = self.config.CRYPTO_ID_MAP[code]
            price_entry = data.get(coin_id, {})
            price = price_entry.get(self.config.BASE_CURRENCY.lower())
            if price is None:
                continue
            rates[f"{code}_{self.config.BASE_CURRENCY}"] = float(price)
        if not rates:
            raise ApiRequestError("CoinGecko вернул пустой набор курсов")
        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Загружает курсы фиатных валют из ExchangeRate-API."""

    def fetch_rates(self) -> Dict[str, float]:
        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/latest/"
            f"{self.config.BASE_CURRENCY}"
        )
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
        rates: Dict[str, float] = {}
        for code in self.config.FIAT_CURRENCIES:
            rate = payload.get("rates", {}).get(code)
            if rate is None:
                continue
            rates[f"{code}_{self.config.BASE_CURRENCY}"] = float(rate)
        if not rates:
            raise ApiRequestError("ExchangeRate-API не вернул ни одного курса")
        return rates


coin_gecko_client = CoinGeckoClient(parser_config)
exchange_rate_client = ExchangeRateApiClient(parser_config)
