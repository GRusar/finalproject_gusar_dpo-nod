"""Командный интерфейс ValutaTrade Hub."""

import shlex
from typing import Any, Dict, Sequence

from valutatrade_hub.cli import constants
from valutatrade_hub.cli.command_parser import build_parser
from valutatrade_hub.core import usecases
from valutatrade_hub.core.currencies import CURRENCY_REGISTRY
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.api_clients import (
    coin_gecko_client,
    exchange_rate_client,
)
from valutatrade_hub.parser_service.config import parser_config
from valutatrade_hub.parser_service.storage import rates_storage
from valutatrade_hub.parser_service.updater import RatesUpdater

CURRENT_SESSION: dict[str, Any] = {"user_id": None, "username": None}
HANDLED_ERRORS = (
    ValueError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    ApiRequestError,
)


def _list_supported_currencies() -> str:
    codes = sorted(CURRENCY_REGISTRY.keys())
    return ", ".join(codes)


def _print_error(error: Exception) -> None:
    if isinstance(error, CurrencyNotFoundError):
        codes = _list_supported_currencies()
        print(f"{error}. Поддерживаемые коды: {codes}")
    elif isinstance(error, ApiRequestError):
        print(f"{error} Проверьте сетевое подключение или попробуйте позже.")
    else:
        print(error)


def update_rates_command(source: str | None) -> None:
    settings = SettingsLoader()
    client_map = {
        "coingecko": coin_gecko_client,
        "exchangerate": exchange_rate_client,
        "exchangerate-api": exchange_rate_client,
    }
    if source and source not in client_map:
        print("Неизвестный источник. Доступны: coingecko, exchangerate")
        return
    clients = (
        [client_map[source]]
        if source
        else [coin_gecko_client, exchange_rate_client]
    )
    updater = RatesUpdater(clients)
    try:
        result = updater.run_update(
            active_sources=[source] if source else None,
        )
    except ApiRequestError as error:
        _print_error(error)
        return
    if result["errors"]:
        print("Обновление выполнено с ошибками. См. логи.")
        for message in result["errors"]:
            print(f"- {message}")
        print(f"Лог: {settings.get('PARSER_LOG_PATH')}")
    else:
        print("Обновление курсов выполнено успешно.")
    print(
        f"Всего обновлено пар: {result['total_rates']}. "
        f"Последнее обновление: {result['last_refresh']}",
    )


def show_rates_command(
    currency: str | None,
    top: int | None,
    base: str | None,
) -> None:
    data = rates_storage.read_rates()
    pairs: Dict[str, Dict[str, Any]] = data.get("pairs", {})
    if not pairs:
        print("Локальный кеш курсов пуст. Выполните 'update-rates'.")
        return

    target_base = (base or parser_config.BASE_CURRENCY).upper()
    requested_currency = currency.upper() if currency else None

    def convert_rate(pair_rate: float, pair_base: str) -> float | None:
        if pair_base == target_base:
            return pair_rate
        if pair_base != parser_config.BASE_CURRENCY:
            return None
        target_pair = pairs.get(
            f"{target_base}_{parser_config.BASE_CURRENCY}",
        )
        if not target_pair:
            return None
        base_rate = target_pair["rate"]
        if base_rate == 0:
            return None
        return pair_rate / base_rate

    entries = []
    for pair, info in pairs.items():
        from_code, pair_base = pair.split("_", 1)
        if requested_currency and from_code != requested_currency:
            continue
        converted = convert_rate(info["rate"], pair_base)
        if converted is None:
            continue
        entries.append(
            {
                "pair": f"{from_code}_{target_base}",
                "rate": converted,
                "source": info.get("source"),
                "updated_at": info.get("updated_at"),
                "is_crypto": from_code in parser_config.CRYPTO_CURRENCIES,
            },
        )

    if requested_currency and not entries:
        print(f"Курс для '{requested_currency}' не найден в кеше.")
        return

    if top:
        crypto_entries = [e for e in entries if e["is_crypto"]]
        entries = sorted(
            crypto_entries,
            key=lambda e: e["rate"],
            reverse=True,
        )[:top]
    else:
        entries.sort(key=lambda e: e["pair"])

    if not entries:
        print("Нет записей, удовлетворяющих фильтрам.")
        return

    last_refresh = data.get("last_refresh") or "неизвестно"
    print(f"Rates from cache (updated at {last_refresh}):")
    for entry in entries:
        print(
            f"- {entry['pair']}: {entry['rate']:.6f} "
            f"(source: {entry['source']}, updated_at={entry['updated_at']})",
        )


def register(username: str, password: str) -> None:
    """Обработчик команды register."""
    try:
        result = usecases.register_user(username=username, password=password)
    except HANDLED_ERRORS as error:
        _print_error(error)
        return

    user = result["username"]
    user_id = result["user_id"]
    print(
        f"Пользователь '{user}' зарегистрирован (id={user_id}). "
        f"Войдите: login --username {user} --password ****",
    )


def login(username: str, password: str) -> None:
    """Обработчик команды login."""
    try:
        result = usecases.login_user(username=username, password=password)
    except HANDLED_ERRORS as error:
        _print_error(error)
        return

    CURRENT_SESSION["user_id"] = result["user_id"]
    CURRENT_SESSION["username"] = result["username"]
    print(f"Вы вошли как '{result['username']}' (id={result['user_id']})")


def show_portfolio(base_currency: str = "USD") -> None:
    """Обработчик команды show-portfolio."""
    if not CURRENT_SESSION.get("user_id"):
        print("Сначала выполните login")
        return

    try:
        report = usecases.show_portfolio(
            user_id=CURRENT_SESSION["user_id"],
            base_currency=base_currency,
        )
    except HANDLED_ERRORS as error:
        _print_error(error)
        return

    wallets = report["wallets"]
    normalized_base = report["base_currency"]
    total = report["total_in_base"]
    username = CURRENT_SESSION.get("username") or "unknown"

    if not wallets:
        print(f"Портфель пользователя '{username}' пуст.")
        return

    print(f"Портфель пользователя '{username}' (база: {normalized_base}):")
    for wallet in wallets:
        currency = wallet["currency_code"]
        balance = wallet["balance"]
        value = wallet["value_in_base"]
        print(
            f"- {currency}: {balance:.4f}  → {value:,.2f} {normalized_base}",
        )
    print("---------------------------------")
    print(f"ИТОГО: {total:,.2f} {normalized_base}")


def buy(currency_code: str, amount: float) -> None:
    """Обработчик команды buy."""
    if not CURRENT_SESSION.get("user_id"):
        print("Сначала выполните login")
        return

    try:
        result = usecases.buy_currency(
            user_id=CURRENT_SESSION["user_id"],
            currency_code=currency_code,
            amount=amount,
        )
    except HANDLED_ERRORS as error:
        _print_error(error)
        return

    code = result["currency_code"]
    purchase_amount = result["amount"]
    previous = result["previous_balance"]
    new_balance = result["new_balance"]
    rate = result["rate_to_usd"]
    estimated_value = result["estimated_value_usd"]

    if rate is not None:
        print(
            f"Покупка выполнена: {purchase_amount:.4f} {code} "
            f"по курсу {rate:,.2f} USD/{code}",
        )
    else:
        print(
            f"Покупка выполнена: {purchase_amount:.4f} {code}. "
            "Курс недоступен.",
        )
    changes_line = (
        f"Изменения в портфеле:\n- {code}: было {previous:.4f} → "
        f"стало {new_balance:.4f}"
    )
    print(changes_line)
    if estimated_value is not None:
        print(f"Оценочная стоимость покупки: {estimated_value:,.2f} USD")


def sell(currency_code: str, amount: float) -> None:
    """Обработчик команды sell."""
    if not CURRENT_SESSION.get("user_id"):
        print("Сначала выполните login")
        return

    try:
        result = usecases.sell_currency(
            user_id=CURRENT_SESSION["user_id"],
            currency_code=currency_code,
            amount=amount,
        )
    except HANDLED_ERRORS as error:
        _print_error(error)
        return

    code = result["currency_code"]
    sell_amount = result["amount"]
    previous = result["previous_balance"]
    new_balance = result["new_balance"]
    rate = result["rate_to_usd"]
    estimated_value = result["estimated_value_usd"]

    if rate is not None:
        print(
            f"Продажа выполнена: {sell_amount:.4f} {code} "
            f"по курсу {rate:,.2f} USD/{code}",
        )
    else:
        print(
            f"Продажа выполнена: {sell_amount:.4f} {code}. "
            "Курс недоступен.",
        )
    changes_line = (
        f"Изменения в портфеле:\n- {code}: было {previous:.4f} → "
        f"стало {new_balance:.4f}"
    )
    print(changes_line)
    if estimated_value is not None:
        print(f"Оценочная выручка: {estimated_value:,.2f} USD")


def get_rate(from_code: str, to_code: str) -> None:
    """Обработчик команды get-rate."""
    try:
        result = usecases.get_exchange_rate(from_code=from_code, to_code=to_code)
    except HANDLED_ERRORS as error:
        _print_error(error)
        return

    rate = result["rate"]
    updated = result.get("updated_at") or "неизвестно"
    normalized_from = result["from_code"]
    normalized_to = result["to_code"]
    inverse_rate = result.get("inverse_rate")

    print(
        f"Курс {normalized_from}→{normalized_to}: {rate:.8f} "
        f"(обновлено: {updated})",
    )
    if inverse_rate:
        print(
            f"Обратный курс {normalized_to}→{normalized_from}: {inverse_rate:.8f}",
        )
    if result.get("stale"):
        warning = result.get("warning") or "Данные устарели. Запустите Parser Service."
        print(f"Внимание: {warning}")


def _dispatch_command(args) -> None:
    """Вызвать функцию-обработчик в зависимости от команды."""
    match args.command:
        case "register":
            register(args.username, args.password)
        case "login":
            login(args.username, args.password)
        case "show-portfolio":
            show_portfolio(args.base)
        case "buy":
            buy(args.currency, args.amount)
        case "sell":
            sell(args.currency, args.amount)
        case "get-rate":
            get_rate(args.from_code, args.to_code)
        case "update-rates":
            update_rates_command(args.source)
        case "show-rates":
            show_rates_command(args.currency, args.top, args.base)
        case _:
            print(f"Неизвестная команда: {args.command}")


def run_cli(argv: Sequence[str] | None = None) -> None:
    """Запустить CLI в пакетном режиме или интерактивной оболочке."""
    parser = build_parser()
    if argv:
        try:
            parsed = parser.parse_args(argv)
        except ValueError as error:
            print(error)
            return
        _dispatch_command(parsed)
        return

    print("ValutaTrade Hub CLI.")
    show_help()
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            print()
            break

        if not line:
            continue
        if line.lower() in {"exit", "quit"}:
            break

        try:
            tokens = shlex.split(line)
        except ValueError as error:
            print(f"Ошибка парсинга команды: {error}")
            continue

        if not tokens:
            continue

        try:
            parsed = parser.parse_args(tokens)
        except ValueError as error:
            print(error)
            continue

        _dispatch_command(parsed)

def show_help(commands: dict[str, str] = constants.COMMANDS) -> None:
    """Выводит справку по доступным командам."""
    print("\nДоступные команды:")
    for command, description in commands.items():
        print(
            f"{command.ljust(constants.HELP_ALIGNMENT, ' ')}{description}"
        )
