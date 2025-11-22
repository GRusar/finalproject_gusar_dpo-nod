"""Репозиторий для загрузки и сохранения портфелей пользователей."""

from __future__ import annotations

from typing import Dict

from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.infra.database import DatabaseManager


class PortfolioRepository:
    """Отвечает за преобразование между JSON-хранилищем и моделями портфеля."""

    def __init__(self, db: DatabaseManager | None = None) -> None:
        self.db = db or DatabaseManager()

    def _load_user(self, user_id: int) -> User:
        users = self.db.read("users", default=[])
        if not isinstance(users, list):
            raise ValueError("Некорректный формат файла users.json")
        record = next((u for u in users if u.get("user_id") == user_id), None)
        if record is None:
            raise ValueError("Пользователь не найден")
        return User(
            user_id=record["user_id"],
            username=record["username"],
            hashed_password=record.get("hashed_password"),
            salt=record.get("salt"),
            registration_date=record.get("registration_date"),
        )

    def load(self, user_id: int) -> Portfolio:
        portfolios = self.db.read("portfolios", default=[])
        if not isinstance(portfolios, list):
            raise ValueError("Некорректный формат файла portfolios.json")
        record = next((p for p in portfolios if p.get("user_id") == user_id), None)
        if record is None:
            raise ValueError("Портфель пользователя не найден")
        wallets_raw = record.get("wallets", {})
        if not isinstance(wallets_raw, dict):
            raise ValueError("Некорректный формат кошельков")

        wallets: Dict[str, Wallet] = {}
        for code, info in wallets_raw.items():
            currency_code = (code or "").strip().upper()
            if not currency_code:
                continue
            balance = float(info.get("balance", 0.0))
            wallets[currency_code] = Wallet(currency_code, initial_balance=balance)

        user = self._load_user(user_id)
        # сохраняем исходный срез для последующей записи
        portfolio = Portfolio(user, wallets)
        portfolio._raw_storage = (record, portfolios)  # type: ignore[attr-defined]
        return portfolio

    def save(self, portfolio: Portfolio) -> None:
        raw = getattr(portfolio, "_raw_storage", None)  # type: ignore[attr-defined]
        if not raw:
            raise ValueError("Отсутствует контекст хранения для портфеля")
        record, portfolios = raw  # type: ignore[misc]
        if not isinstance(record, dict) or not isinstance(portfolios, list):
            raise ValueError("Некорректный формат данных портфеля")
        record["wallets"] = {
            code: wallet.get_balance_info()
            for code, wallet in portfolio.wallets.items()
        }
        self.db.write("portfolios", portfolios)
