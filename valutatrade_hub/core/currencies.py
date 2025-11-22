"""Типы валют и фабрика для получения экземпляров."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Базовый класс валюты."""

    def __init__(self, name: str, code: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Имя валюты не может быть пустым")
        if not isinstance(code, str):
            raise ValueError("Код валюты должен быть строкой")
        normalized_code = code.strip().upper()
        if not 2 <= len(normalized_code) <= 5 or " " in normalized_code:
            raise ValueError("Код валюты должен быть от 2 до 5 символов без пробелов")

        self._name = name.strip()
        self._code = normalized_code

    @property
    def name(self) -> str:
        return self._name

    @property
    def code(self) -> str:
        return self._code

    @abstractmethod
    def get_display_info(self) -> str:
        """Вернуть человекочитаемое описание валюты."""


class FiatCurrency(Currency):
    """Фиатная валюта с указанием страны-эмитента."""

    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        super().__init__(name, code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна-эмитент должна быть задана")
        self._issuing_country = issuing_country.strip()

    @property
    def issuing_country(self) -> str:
        return self._issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта с указанием алгоритма и капитализации."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float) -> None:
        super().__init__(name, code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм должен быть задан")
        if not isinstance(market_cap, (int, float)) or market_cap < 0:
            raise ValueError("Капитализация должна быть неотрицательным числом")
        self._algorithm = algorithm.strip()
        self._market_cap = float(market_cap)

    @property
    def algorithm(self) -> str:
        return self._algorithm

    @property
    def market_cap(self) -> float:
        return self._market_cap

    def get_display_info(self) -> str:
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


CURRENCY_REGISTRY: Dict[str, Currency] = {
    "USD": FiatCurrency(name="US Dollar", code="USD", issuing_country="United States"),
    "EUR": FiatCurrency(name="Euro", code="EUR", issuing_country="Eurozone"),
    "RUB": FiatCurrency(name="Russian Ruble", code="RUB", issuing_country="Russia"),
    "BTC": CryptoCurrency(
        name="Bitcoin",
        code="BTC",
        algorithm="SHA-256",
        market_cap=1.0e12,
    ),
    "ETH": CryptoCurrency(
        name="Ethereum",
        code="ETH",
        algorithm="Ethash",
        market_cap=4.0e11,
    ),
}


def get_currency(code: str) -> Currency:
    """Возвращает валюту из реестра или вызывает CurrencyNotFoundError."""
    normalized = (code or "").strip().upper()
    if not normalized:
        raise CurrencyNotFoundError("")
    try:
        return CURRENCY_REGISTRY[normalized]
    except KeyError as exc:
        raise CurrencyNotFoundError(normalized) from exc
