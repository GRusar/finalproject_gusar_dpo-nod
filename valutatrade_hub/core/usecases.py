"""Бизнес-логика платформы ValutaTrade Hub."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import parse_iso_datetime
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import settings

db_manager = DatabaseManager()


def _extract_value(args: tuple, kwargs: dict, key: str, index: int) -> Any:
    """Возвращает значение аргумента из kwargs или args."""
    if key in kwargs:
        return kwargs[key]
    if len(args) > index:
        return args[index]
    return None


def _build_trade_context(
    args: tuple,
    kwargs: dict,
    result: Optional[dict[str, Any]],
    verbose: bool,
) -> dict[str, Any]:
    """Формирует контекст лога для торговых операций (buy/sell)."""
    context: dict[str, Any] = {
        "user_id": _extract_value(args, kwargs, "user_id", 0),
        "currency": _extract_value(args, kwargs, "currency_code", 1),
        "amount": _extract_value(args, kwargs, "amount", 2),
        "base": settings.get("DEFAULT_BASE_CURRENCY", "USD"),
    }
    if result:
        context["currency"] = result.get("currency_code", context["currency"])
        context["base"] = result.get("base_currency", context["base"])
        rate = result.get("rate_to_base") or result.get("rate_to_usd")
        if rate is not None:
            context["rate"] = rate
        if verbose:
            context["balance_before"] = result.get("previous_balance")
            context["balance_after"] = result.get("new_balance")
            if result.get("estimated_value_base") is not None:
                context["estimated_base"] = result["estimated_value_base"]
            elif result.get("estimated_value_usd") is not None:
                context["estimated_usd"] = result["estimated_value_usd"]
    return {k: v for k, v in context.items() if v is not None}


def _build_usd_rates(rates_data: Dict[str, Any]) -> Dict[str, float]:
    """Строит карту «валюта → курс к USD» из данных кеша."""
    pairs_section = rates_data.get("pairs")
    if isinstance(pairs_section, dict):
        raw_pairs = pairs_section
    else:
        raw_pairs = rates_data

    rates: Dict[str, float] = {"USD": 1.0}
    for pair, info in raw_pairs.items():
        if pair in {"last_refresh", "source"}:
            continue
        if not isinstance(info, dict) or "_" not in pair:
            continue
        if "rate" not in info:
            continue
        try:
            rate_value = float(info["rate"])
        except (TypeError, ValueError):
            continue
        from_code, to_code = pair.split("_", 1)
        from_code = from_code.upper()
        to_code = to_code.upper()

        if to_code == "USD":
            rates[from_code] = rate_value
        elif from_code == "USD" and rate_value != 0:
            rates[to_code] = 1 / rate_value
    return rates


def _load_exchange_rates() -> Dict[str, float]:
    """Подтягивает курсы валют из кеша и возвращает словарь курсов к USD."""
    rates_data = db_manager.read("rates", default={})
    if not isinstance(rates_data, dict):
        raise ValueError("Некорректный формат файла rates.json")

    rates = _build_usd_rates(rates_data)
    if len(rates) <= 1:
        raise ValueError("В кеше отсутствуют данные о курсах")
    return rates


def _load_user_by_id(user_id: int) -> User:
    users_data = db_manager.read("users", default=[])
    if not isinstance(users_data, list):
        raise ValueError("Некорректный формат файла users.json")
    record = next((user for user in users_data if user.get("user_id") == user_id), None)
    if record is None:
        raise ValueError("Пользователь не найден")
    return User(
        user_id=record["user_id"],
        username=record["username"],
        hashed_password=record.get("hashed_password"),
        salt=record.get("salt"),
        registration_date=record.get("registration_date"),
    )


def _load_portfolio_for_user(
    user_id: int,
) -> tuple[Portfolio, dict[str, Any], list[dict]]:
    portfolios = db_manager.read("portfolios", default=[])
    if not isinstance(portfolios, list):
        raise ValueError("Некорректный формат файла portfolios.json")
    record = next((p for p in portfolios if p.get("user_id") == user_id), None)
    if record is None:
        raise ValueError("Портфель пользователя не найден")
    wallets_raw = record.get("wallets", {})
    if not isinstance(wallets_raw, dict):
        raise ValueError("Некорректный формат кошельков")

    wallets: dict[str, Wallet] = {}
    for code, info in wallets_raw.items():
        currency_code = (code or "").strip().upper()
        if not currency_code:
            continue
        balance = float(info.get("balance", 0.0))
        wallets[currency_code] = Wallet(currency_code, initial_balance=balance)

    user = _load_user_by_id(user_id)
    portfolio = Portfolio(user, wallets)
    return portfolio, record, portfolios


def _save_portfolio(
    portfolio: Portfolio,
    portfolio_record: dict[str, Any],
    portfolios: list[dict],
) -> None:
    portfolio_record["wallets"] = {
        code: wallet.get_balance_info() for code, wallet in portfolio.wallets.items()
    }
    db_manager.write("portfolios", portfolios)


def _calc_base_conversion(
    currency_code: str,
    base_currency: str,
    exchange_rates: Dict[str, float],
    amount: float,
) -> tuple[float | None, float | None, float | None, str]:
    """
    Возвращает (rate_to_usd, rate_to_base, estimated_in_base, normalized_base).
    Конвертация всегда идёт через USD, поскольку exchange_rates хранятся к USD.
    """
    normalized_base = base_currency.upper()
    rate_to_usd = exchange_rates.get(currency_code)
    base_rate_usd = exchange_rates.get(normalized_base)
    rate_to_base: float | None = None
    estimated_value_base: float | None = None
    if rate_to_usd is not None:
        if normalized_base == "USD":
            rate_to_base = rate_to_usd
        elif base_rate_usd:
            rate_to_base = rate_to_usd / base_rate_usd
        if rate_to_base is not None:
            estimated_value_base = amount * rate_to_base
    return rate_to_usd, rate_to_base, estimated_value_base, normalized_base


def _is_rates_fresh(rates_data: Dict[str, Any]) -> bool:
    ttl_seconds = int(settings.get("RATES_TTL_SECONDS", 300))
    last_refresh = parse_iso_datetime(rates_data.get("last_refresh"))
    if last_refresh is None:
        return False
    return datetime.now(timezone.utc) - last_refresh <= timedelta(seconds=ttl_seconds)


def _refresh_rates_cache(current_data: Dict[str, Any]) -> Dict[str, Any]:
    """Попытка обновить кеш курсов (заглушка до подключения Parser Service)."""
    raise ApiRequestError(
        "Обновление курсов пока недоступно. Запустите Parser Service.",
    )


def register_user(username: str, password: str) -> dict[str, Any]:
    """Функция регистрации."""
    normalized_username = (username or "").strip()
    if not normalized_username:
        raise ValueError("Имя пользователя не может быть пустым")
    if len(password or "") < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users_data = db_manager.read("users", default=[])
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
    db_manager.write("users", users_data)

    portfolios = db_manager.read("portfolios", default=[])
    if not isinstance(portfolios, list):
        raise ValueError("Некорректный формат файла portfolios.json")
    portfolios.append({"user_id": new_user_id, "wallets": {}})
    db_manager.write("portfolios", portfolios)

    return {"user_id": new_user_id, "username": user.username}


def login_user(username: str, password: str) -> dict[str, Any]:
    """Функция логина."""
    normalized_username = (username or "").strip()
    if not normalized_username:
        raise ValueError("Имя пользователя не может быть пустым")

    users_data = db_manager.read("users", default=[])
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


def show_portfolio(user_id: int, base_currency: str | None = None) -> dict[str, Any]:
    """Возвращает состояние портфеля и пересчитывает суммы в базовую валюту."""
    default_base = settings.get("DEFAULT_BASE_CURRENCY", "USD")
    normalized_base = (base_currency or default_base).strip().upper()
    portfolio, _, _ = _load_portfolio_for_user(user_id)
    exchange_rates = _load_exchange_rates()
    if normalized_base not in exchange_rates:
        raise ValueError(f"Неизвестная базовая валюта '{normalized_base}'")

    wallets_info: list[dict[str, float | str]] = []
    for wallet in portfolio.wallets.values():
        rate_to_usd, rate_to_base, estimated_value_base, _ = _calc_base_conversion(
            wallet.currency_code,
            normalized_base,
            exchange_rates,
            wallet.balance,
        )
        if rate_to_usd is None:
            raise ValueError(f"Нет курса для валюты '{wallet.currency_code}'")
        value_in_base = (
            estimated_value_base if estimated_value_base is not None else 0.0
        )
        wallets_info.append(
            {
                "currency_code": wallet.currency_code,
                "balance": wallet.balance,
                "value_in_base": value_in_base,
            },
        )

    total_in_base = portfolio.get_total_value(
        base_currency=normalized_base,
        exchange_rates=exchange_rates,
    )

    return {
        "wallets": wallets_info,
        "base_currency": normalized_base,
        "total_in_base": total_in_base,
    }


@log_action(action="BUY", context_getter=_build_trade_context, verbose=True)
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

    currency = get_currency(currency_code)
    normalized_code = currency.code

    portfolio, portfolio_record, portfolios = _load_portfolio_for_user(user_id)
    wallet = portfolio.get_wallet(normalized_code)
    if wallet is None:
        wallet = portfolio.add_currency(normalized_code)

    previous_balance = wallet.balance
    wallet.deposit(amount_value)
    new_balance = wallet.balance

    _save_portfolio(portfolio, portfolio_record, portfolios)

    exchange_rates = _load_exchange_rates()
    default_base = str(settings.get("DEFAULT_BASE_CURRENCY", "USD")).upper()
    rate_to_usd, rate_to_base, estimated_value_base, normalized_base = (
        _calc_base_conversion(
            normalized_code,
            default_base,
            exchange_rates,
            amount_value,
        )
    )

    return {
        "currency_code": normalized_code,
        "amount": amount_value,
        "previous_balance": previous_balance,
        "new_balance": new_balance,
        "rate_to_usd": rate_to_usd,
        "rate_to_base": rate_to_base,
        "estimated_value_base": estimated_value_base,
        "base_currency": normalized_base,
    }


@log_action(action="SELL", context_getter=_build_trade_context, verbose=True)
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

    currency = get_currency(currency_code)
    normalized_code = currency.code

    portfolio, portfolio_record, portfolios = _load_portfolio_for_user(user_id)
    wallet = portfolio.get_wallet(normalized_code)
    if wallet is None:
        raise ValueError(f"У вас нет кошелька '{normalized_code}'. Добавьте валюту.")

    previous_balance = wallet.balance
    wallet.withdraw(amount_value)
    new_balance = wallet.balance
    _save_portfolio(portfolio, portfolio_record, portfolios)

    exchange_rates = _load_exchange_rates()
    default_base = str(settings.get("DEFAULT_BASE_CURRENCY", "USD")).upper()
    rate_to_usd, rate_to_base, estimated_value_base, normalized_base = (
        _calc_base_conversion(
            normalized_code,
            default_base,
            exchange_rates,
            amount_value,
        )
    )

    return {
        "currency_code": normalized_code,
        "amount": amount_value,
        "previous_balance": previous_balance,
        "new_balance": new_balance,
        "rate_to_usd": rate_to_usd,
        "rate_to_base": rate_to_base,
        "estimated_value_base": estimated_value_base,
        "base_currency": normalized_base,
    }


def get_exchange_rate(from_code: str, to_code: str) -> dict[str, Any]:
    """Функция получения курса обмена."""
    from_currency = get_currency(from_code)
    to_currency = get_currency(to_code)
    normalized_from = from_currency.code
    normalized_to = to_currency.code

    if normalized_from == normalized_to:
        return {
            "from_code": normalized_from,
            "to_code": normalized_to,
            "rate": 1.0,
            "updated_at": None,
            "inverse_rate": 1.0,
            "stale": False,
        }

    rates_data = db_manager.read("rates", default={})
    if not isinstance(rates_data, dict):
        raise ValueError("Некорректный формат файла rates.json")

    stale = False
    warning: Optional[str] = None
    if not _is_rates_fresh(rates_data):
        stale = True
        try:
            refreshed = _refresh_rates_cache(rates_data)
        except ApiRequestError as error:
            warning = str(error)
            if not rates_data:
                raise
        else:
            rates_data = refreshed
            stale = False

    usd_rates = _build_usd_rates(rates_data)
    if normalized_from not in usd_rates:
        raise ValueError(f"Не удалось получить курс для {normalized_from}")
    if normalized_to not in usd_rates:
        raise ValueError(f"Не удалось получить курс для {normalized_to}")

    from_to_usd = usd_rates[normalized_from]
    to_to_usd = usd_rates[normalized_to]
    if to_to_usd == 0:
        raise ValueError(f"Некорректный курс для валюты {normalized_to}")

    rate_value = from_to_usd / to_to_usd
    updated_at = rates_data.get("last_refresh")
    result = {
        "from_code": normalized_from,
        "to_code": normalized_to,
        "rate": rate_value,
        "updated_at": updated_at,
        "inverse_rate": None if rate_value == 0 else 1 / rate_value,
        "stale": stale,
    }
    if warning:
        result["warning"] = warning
    return result
