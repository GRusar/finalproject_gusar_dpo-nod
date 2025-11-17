"""Конфигурация Parser Service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"


def _get_api_key() -> str:
    """Возвращает API-ключ (сначала ищет в окружении, затем в .env)."""
    env_key = os.getenv("EXCHANGERATE_API_KEY")
    if env_key:
        return env_key
    if ENV_PATH.exists():
        for raw_line in ENV_PATH.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "EXCHANGERATE_API_KEY":
                return value.strip().strip("'\"")
    raise RuntimeError("EXCHANGERATE_API_KEY отсутствует и в окружении, и в .env")


@dataclass
class ParserConfig:
    """Хранит настройки источников курсов и хранения файлов."""

    # Ключ загружается из переменной окружения/.env (лениво)
    EXCHANGERATE_API_KEY: str | None = None

    # Эндпоинты
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Списки валют
    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple[str, ...] = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        },
    )

    # Пути
    RATES_FILE_PATH: str = str(PROJECT_ROOT / "data" / "rates.json")
    HISTORY_FILE_PATH: str = str(PROJECT_ROOT / "data" / "exchange_rates.json")

    # Сетевые параметры
    REQUEST_TIMEOUT: int = 10

    def get_exchange_api_key(self) -> str:
        """Возвращает API-ключ, загружая его при необходимости."""
        if self.EXCHANGERATE_API_KEY:
            return self.EXCHANGERATE_API_KEY

        api_key = _get_api_key()
        self.EXCHANGERATE_API_KEY = api_key
        return api_key


parser_config = ParserConfig()
