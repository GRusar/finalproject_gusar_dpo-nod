"""Бизнес-логика платформы ValutaTrade Hub."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from valutatrade_hub.core.models import DEFAULT_EXCHANGE_RATES, User

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"


def _load_json(path: Path, default: Any) -> Any:
    """Загрузка данных из json"""
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return default


def _save_json(path: Path, data: Any) -> None:
    """Простая запись данных в json."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def _load_exchange_rates() -> Dict[str, float]:
    """Подтягивает курсы валют из кеша и накладывает их на значения по умолчанию."""
    rates_data = _load_json(RATES_FILE, default={})
    merged_rates = dict(DEFAULT_EXCHANGE_RATES)

    if isinstance(rates_data, dict):
        for pair, info in rates_data.items():
            if not isinstance(info, dict):
                continue
            if "_" not in pair or "rate" not in info:
                continue
            from_code, to_code = pair.split("_", 1)
            from_code = from_code.upper()
            to_code = to_code.upper()
            try:
                rate_value = float(info["rate"])
            except (TypeError, ValueError):
                continue
            if to_code == "USD":
                merged_rates[from_code] = rate_value
            elif from_code == "USD" and rate_value != 0:
                merged_rates[to_code] = 1 / rate_value

    return merged_rates


def register_user(username: str, password: str) -> dict[str, Any]:
    """Функция регистрации."""
    normalized_username = (username or "").strip()
    if not normalized_username:
        raise ValueError("Имя пользователя не может быть пустым")
    if len(password or "") < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users_data = _load_json(USERS_FILE, default=[])
    if not isinstance(users_data, list):
        raise ValueError("Некорректный формат файла users.json")
    if any(user.get("username") == normalized_username for user in users_data):
        raise ValueError(f"Имя пользователя '{normalized_username}' уже занято")

    new_user_id = max((user.get("user_id", 0) for user in users_data), default=0) + 1
    user = User(user_id=new_user_id, username=normalized_username)
    user.change_password(password)

    users_data.append(
        {
            "user_id": user.user_id,
            "username": user.username,
            "hashed_password": user.hashed_password,
            "salt": user.salt,
            "registration_date": user.registration_date.isoformat(),
        },
    )
    _save_json(USERS_FILE, users_data)

    portfolios = _load_json(PORTFOLIOS_FILE, default=[])
    if not isinstance(portfolios, list):
        raise ValueError("Некорректный формат файла portfolios.json")
    portfolios.append({"user_id": new_user_id, "wallets": {}})
    _save_json(PORTFOLIOS_FILE, portfolios)

    return {"user_id": new_user_id, "username": user.username}


def login_user(username: str, password: str) -> dict[str, Any]:
    """Функция логина."""
    normalized_username = (username or "").strip()
    if not normalized_username:
        raise ValueError("Имя пользователя не может быть пустым")

    users_data = _load_json(USERS_FILE, default=[])
    if not isinstance(users_data, list):
        raise ValueError("Некорректный формат файла users.json")

    user_record = next(
        (user for user in users_data if user.get("username") == normalized_username),
        None,
    )
    if user_record is None:
        raise ValueError(f"Пользователь '{normalized_username}' не найден")

    user = User(
        user_id=user_record["user_id"],
        username=user_record["username"],
        hashed_password=user_record["hashed_password"],
        salt=user_record["salt"],
        registration_date=user_record["registration_date"],
    )
    if not user.verify_password(password):
        raise ValueError("Неверный пароль")

    return {"user_id": user.user_id, "username": user.username}


def show_portfolio(user_id: int, base_currency: str = "USD") -> dict[str, Any]:
    """Возвращает состояние портфеля и пересчитывает суммы в базовую валюту."""
    normalized_base = (base_currency or "USD").strip().upper()
    portfolios = _load_json(PORTFOLIOS_FILE, default=[])
    if not isinstance(portfolios, list):
        raise ValueError("Некорректный формат файла portfolios.json")

    portfolio_record = next(
        (portfolio for portfolio in portfolios if portfolio.get("user_id") == user_id),
        None,
    )
    if portfolio_record is None:
        raise ValueError("Портфель пользователя не найден")

    wallets_data = portfolio_record.get("wallets", {})
    if not isinstance(wallets_data, dict):
        raise ValueError("Некорректный формат кошельков")

    exchange_rates = _load_exchange_rates()
    if normalized_base not in exchange_rates:
        raise ValueError(f"Неизвестная базовая валюта '{normalized_base}'")

    base_rate_usd = exchange_rates[normalized_base]
    wallets_info: list[dict[str, float | str]] = []
    total_in_base = 0.0

    for code, wallet_info in wallets_data.items():
        currency_code = (code or "").strip().upper()
        if not currency_code:
            continue
        balance = float(wallet_info.get("balance", 0.0))
        rate_to_usd = exchange_rates.get(currency_code)
        if rate_to_usd is None:
            raise ValueError(f"Нет курса для валюты '{currency_code}'")

        value_in_base = balance * rate_to_usd
        if normalized_base != "USD" and base_rate_usd != 0:
            value_in_base /= base_rate_usd

        wallets_info.append(
            {
                "currency_code": currency_code,
                "balance": balance,
                "value_in_base": value_in_base,
            },
        )
        total_in_base += value_in_base

    return {
        "wallets": wallets_info,
        "base_currency": normalized_base,
        "total_in_base": total_in_base,
    }


def buy_currency(user_id: int, currency_code: str, amount: float) -> dict[str, Any]:
    """Функция покупки валюты."""
    if user_id is None:
        raise ValueError("Не указан пользователь")

    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        raise ValueError("'amount' должен быть положительным числом") from None
    if amount_value <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    normalized_code = (currency_code or "").strip().upper()
    if not normalized_code:
        raise ValueError("Код валюты должен быть непустой строкой")

    portfolios = _load_json(PORTFOLIOS_FILE, default=[])
    if not isinstance(portfolios, list):
        raise ValueError("Некорректный формат файла portfolios.json")

    portfolio = next(
        (item for item in portfolios if item.get("user_id") == user_id),
        None,
    )
    if portfolio is None:
        raise ValueError("Портфель пользователя не найден")

    wallets = portfolio.get("wallets")
    if wallets is None or not isinstance(wallets, dict):
        wallets = {}
        portfolio["wallets"] = wallets

    wallet = wallets.get(normalized_code)
    if wallet is None:
        wallet = {"currency_code": normalized_code, "balance": 0.0}
        wallets[normalized_code] = wallet

    previous_balance = float(wallet.get("balance", 0.0))
    new_balance = previous_balance + amount_value
    wallet["currency_code"] = normalized_code
    wallet["balance"] = new_balance

    _save_json(PORTFOLIOS_FILE, portfolios)

    exchange_rates = _load_exchange_rates()
    rate_to_usd = exchange_rates.get(normalized_code)
    estimated_value = amount_value * rate_to_usd if rate_to_usd is not None else None

    return {
        "currency_code": normalized_code,
        "amount": amount_value,
        "previous_balance": previous_balance,
        "new_balance": new_balance,
        "rate_to_usd": rate_to_usd,
        "estimated_value_usd": estimated_value,
    }


def sell_currency(user_id: int, currency_code: str, amount: float) -> dict[str, Any]:
    """Функция продажи валюты."""
    if user_id is None:
        raise ValueError("Не указан пользователь")

    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        raise ValueError("'amount' должен быть положительным числом") from None
    if amount_value <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    normalized_code = (currency_code or "").strip().upper()
    if not normalized_code:
        raise ValueError("Код валюты должен быть непустой строкой")

    portfolios = _load_json(PORTFOLIOS_FILE, default=[])
    if not isinstance(portfolios, list):
        raise ValueError("Некорректный формат файла portfolios.json")

    portfolio = next(
        (item for item in portfolios if item.get("user_id") == user_id),
        None,
    )
    if portfolio is None:
        raise ValueError("Портфель пользователя не найден")

    wallets = portfolio.get("wallets")
    if not isinstance(wallets, dict) or normalized_code not in wallets:
        raise ValueError(f"У вас нет кошелька '{normalized_code}'. Добавьте валюту.")

    wallet = wallets[normalized_code]
    previous_balance = float(wallet.get("balance", 0.0))
    if amount_value > previous_balance:
        raise ValueError(
            f"Недостаточно средств: доступно {previous_balance:.4f} "
            f"{normalized_code}, требуется {amount_value:.4f} {normalized_code}",
        )

    new_balance = previous_balance - amount_value
    wallet["balance"] = new_balance
    _save_json(PORTFOLIOS_FILE, portfolios)

    exchange_rates = _load_exchange_rates()
    rate_to_usd = exchange_rates.get(normalized_code)
    estimated_value = amount_value * rate_to_usd if rate_to_usd is not None else None

    return {
        "currency_code": normalized_code,
        "amount": amount_value,
        "previous_balance": previous_balance,
        "new_balance": new_balance,
        "rate_to_usd": rate_to_usd,
        "estimated_value_usd": estimated_value,
    }


def get_exchange_rate(from_code: str, to_code: str) -> dict[str, Any]:
    """Функция получения курса обмена."""
    normalized_from = (from_code or "").strip().upper()
    normalized_to = (to_code or "").strip().upper()

    if not normalized_from or not normalized_to:
        raise ValueError("Коды валют должны быть непустыми строками")
    if normalized_from == normalized_to:
        return {
            "from_code": normalized_from,
            "to_code": normalized_to,
            "rate": 1.0,
            "updated_at": None,
            "inverse_rate": 1.0,
        }

    rates_data = _load_json(RATES_FILE, default={})
    if rates_data is None:
        rates_data = {}
    if not isinstance(rates_data, dict):
        raise ValueError("Некорректный формат файла rates.json")

    def _extract_pair(pair_from: str, pair_to: str) -> Optional[dict[str, Any]]:
        key = f"{pair_from}_{pair_to}"
        entry = rates_data.get(key)
        if not isinstance(entry, dict):
            return None
        if "rate" not in entry:
            return None
        try:
            rate_value = float(entry["rate"])
        except (TypeError, ValueError):
            return None
        updated_at = entry.get("updated_at") or rates_data.get("last_refresh")
        return {
            "from_code": pair_from,
            "to_code": pair_to,
            "rate": rate_value,
            "updated_at": updated_at,
            "inverse_rate": None if rate_value == 0 else 1 / rate_value,
        }

    direct = _extract_pair(normalized_from, normalized_to)
    if direct:
        return direct

    inverse = _extract_pair(normalized_to, normalized_from)
    if inverse and inverse["rate"]:
        rate_value = 1 / inverse["rate"]
        return {
            "from_code": normalized_from,
            "to_code": normalized_to,
            "rate": rate_value,
            "updated_at": inverse["updated_at"],
            "inverse_rate": inverse["rate"],
        }

    exchange_rates = _load_exchange_rates()
    if normalized_from not in exchange_rates:
        raise ValueError(f"Не удалось получить курс для {normalized_from}")
    if normalized_to not in exchange_rates:
        raise ValueError(f"Не удалось получить курс для {normalized_to}")

    from_to_usd = exchange_rates[normalized_from]
    to_to_usd = exchange_rates[normalized_to]
    if to_to_usd == 0:
        raise ValueError(f"Некорректный курс для валюты {normalized_to}")

    rate_value = from_to_usd / to_to_usd
    updated_at = rates_data.get("last_refresh")

    return {
        "from_code": normalized_from,
        "to_code": normalized_to,
        "rate": rate_value,
        "updated_at": updated_at,
        "inverse_rate": None if rate_value == 0 else 1 / rate_value,
    }
