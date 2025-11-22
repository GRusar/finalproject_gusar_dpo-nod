from __future__ import annotations

from base64 import b64decode, b64encode
from datetime import datetime
from hashlib import sha256
from os import urandom
from typing import Optional

from valutatrade_hub.core.exceptions import InsufficientFundsError


class User:
    """Пользователь в системе."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str | None = None,
        salt: str | None = None,
        registration_date: Optional[datetime | str] = None,
    ) -> None:
        self._user_id = self._validate_user_id(user_id)
        self.username = username
        self._registration_date = self._parse_registration_date(registration_date)
        self._hashed_password = hashed_password or ""
        self._salt = salt or ""

    @staticmethod
    def _validate_user_id(user_id: int) -> int:
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id должен быть положительным целым числом")
        return user_id

    @staticmethod
    def _parse_registration_date(
        registration_date: Optional[datetime | str],
    ) -> datetime:
        if registration_date is None:
            return datetime.now()
        if isinstance(registration_date, datetime):
            return registration_date
        try:
            return datetime.fromisoformat(registration_date)
        except ValueError as exc:
            raise ValueError("registration_date должен быть ISO-датой") from exc

    def get_user_info(self) -> dict[str, str | int]:
        """Выводит информацию о пользователе (без пароля)."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя, с хешированием нового пароля."""
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен содержать минимум 4 символа")
        salt = urandom(16)
        digest = sha256(new_password.encode() + salt).digest()

        self._salt = b64encode(salt).decode()
        self._hashed_password = b64encode(digest).decode()

    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль на совпадение."""
        if not self._salt:
            return False
        salt = b64decode(self._salt)
        hashed = b64encode(sha256(password.encode() + salt).digest()).decode()
        return hashed == self._hashed_password

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, new_username: str) -> None:
        if not isinstance(new_username, str) or not new_username.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = new_username.strip()

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date


class Wallet:
    """Кошелёк пользователя для одной конкретной валюты."""

    def __init__(self, currency_code: str, initial_balance: float = 0.0) -> None:
        self.currency_code = self._normalize_currency_code(currency_code)
        self._balance = 0.0
        self.balance = initial_balance

    @staticmethod
    def _normalize_currency_code(code: str) -> str:
        if not isinstance(code, str) or not code.strip():
            raise ValueError("Код валюты должен быть непустой строкой")
        return code.strip().upper()

    @staticmethod
    def _validate_amount(amount: float) -> float:
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
        return float(amount)

    def deposit(self, amount: float) -> None:
        """Пополнение баланса."""
        value = self._validate_amount(amount)
        self._balance += value

    def withdraw(self, amount: float) -> None:
        """Снятие средств (если баланс позволяет)."""
        value = self._validate_amount(amount)
        if value > self._balance:
            raise InsufficientFundsError(
                available=self._balance,
                required=value,
                code=self.currency_code,
            )
        self._balance -= value

    def get_balance_info(self) -> dict[str, float | str]:
        """Вывод информации о текущем балансе."""
        return {"currency_code": self.currency_code, "balance": self._balance}

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)


class Portfolio:
    """Управление всеми кошельками одного пользователя."""

    def __init__(self, user: User, wallets: Optional[dict[str, Wallet]] = None) -> None:
        self._user = user
        self._user_id = user.user_id
        self._wallets: dict[str, Wallet] = {}
        if wallets:
            for wallet in wallets.values():
                self._wallets[wallet.currency_code] = wallet

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет новый кошелёк в портфель (если его ещё нет)."""
        normalized = Wallet._normalize_currency_code(currency_code)
        if normalized in self._wallets:
            raise ValueError(f"Кошелёк {normalized} уже существует")
        wallet = Wallet(normalized)
        self._wallets[normalized] = wallet
        return wallet

    def get_total_value(
        self,
        base_currency: str = "USD",
        exchange_rates: Optional[dict[str, float]] = None,
    ) -> float:
        """Возвращает общую стоимость всех валют пользователя в базовой валюте."""
        if not exchange_rates:
            raise ValueError("Не переданы курсы для оценки портфеля")
        normalized_base = Wallet._normalize_currency_code(base_currency)
        if normalized_base not in exchange_rates:
            raise ValueError(f"Нет курса для базовой валюты {normalized_base}")

        total_in_usd = 0.0
        for wallet in self._wallets.values():
            code = wallet.currency_code
            if code not in exchange_rates:
                raise ValueError(f"Нет курса для валюты {code}")
            total_in_usd += wallet.balance * exchange_rates[code]

        if normalized_base == "USD":
            return total_in_usd
        return total_in_usd / exchange_rates[normalized_base]

    def get_wallet(self, currency_code: str) -> Optional[Wallet]:
        """Возвращает объект Wallet по коду валюты."""
        normalized = Wallet._normalize_currency_code(currency_code)
        return self._wallets.get(normalized)

    @property
    def user(self) -> User:
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        return dict(self._wallets)
