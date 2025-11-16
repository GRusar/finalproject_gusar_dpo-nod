"""Командный интерфейс ValutaTrade Hub."""

import shlex
from typing import Any, Sequence

from valutatrade_hub.cli import constants
from valutatrade_hub.cli.command_parser import build_parser
from valutatrade_hub.core import usecases
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)

CURRENT_SESSION: dict[str, Any] = {"user_id": None, "username": None}
HANDLED_ERRORS = (ValueError, CurrencyNotFoundError, InsufficientFundsError, ApiRequestError)


def register(username: str, password: str) -> None:
    """Обработчик команды register."""
    try:
        result = usecases.register_user(username=username, password=password)
    except HANDLED_ERRORS as error:
        print(error)
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
        print(error)
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
        print(error)
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
        print(error)
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
        print(error)
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
        print(error)
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
