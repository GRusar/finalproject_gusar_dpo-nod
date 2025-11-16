
"""Командный интерфейс ValutaTrade Hub."""

from typing import Any

from valutatrade_hub.core import usecases

CURRENT_SESSION: dict[str, Any] = {"user_id": None, "username": None}


def register_command(username: str, password: str) -> None:
    """
    Команда register:
    * принимает обязательные --username и --password;
    * проверяет уникальность имени, хеширует пароль, создаёт запись в users.json;
    * создаёт пустой портфель и сообщает об успешной регистрации.
    """
    normalized_username = (username or "").strip()
    try:
        user_id = usecases.register_user(username=normalized_username, password=password)
    except ValueError as error:
        print(error)
        return

    print(
        f"Пользователь '{normalized_username}' зарегистрирован (id={user_id}). "
        f"Войдите: login --username {normalized_username} --password ****",
    )


def login_command(username: str, password: str) -> None:
    """
    Команда login:
    * принимает --username и --password;
    * ищет пользователя и проверяет пароль;
    * фиксирует текущую сессию.
    """
    normalized_username = (username or "").strip()
    try:
        user_id = usecases.login_user(username=normalized_username, password=password)
    except ValueError as error:
        print(error)
        return

    CURRENT_SESSION["user_id"] = user_id
    CURRENT_SESSION["username"] = normalized_username
    print(f"Вы вошли как '{normalized_username}' (id={user_id})")


def show_portfolio_command(base_currency: str = "USD") -> None:
    """
    Команда show-portfolio:
    * доступна только залогиненному пользователю;
    * выводит все кошельки и стоимость в базовой валюте (по умолчанию USD);
    * принимает опциональный --base.
    """
    if not CURRENT_SESSION.get("user_id"):
        print("Сначала выполните login")
        return

    try:
        report = usecases.show_portfolio(
            user_id=CURRENT_SESSION["user_id"],
            base_currency=base_currency,
        )
    except ValueError as error:
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


def buy_command(currency_code: str, amount: float) -> None:
    """
    Команда buy:
    * требует логина;
    * проверяет --currency и положительный --amount;
    * создаёт кошелёк при необходимости и увеличивает баланс.
    """
    if not CURRENT_SESSION.get("user_id"):
        print("Сначала выполните login")
        return

    try:
        result = usecases.buy_currency(
            user_id=CURRENT_SESSION["user_id"],
            currency_code=currency_code,
            amount=amount,
        )
    except ValueError as error:
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
    print(
        f"Изменения в портфеле:\n- {code}: было {previous:.4f} → стало {new_balance:.4f}",
    )
    if estimated_value is not None:
        print(f"Оценочная стоимость покупки: {estimated_value:,.2f} USD")


def sell_command(currency_code: str, amount: float) -> None:
    """
    Команда sell:
    * требует логина;
    * проверяет существование кошелька и достаточно ли средств;
    * уменьшает баланс и может показывать оценочную выручку.
    """
    if not CURRENT_SESSION.get("user_id"):
        print("Сначала выполните login")
        return

    try:
        result = usecases.sell_currency(
            user_id=CURRENT_SESSION["user_id"],
            currency_code=currency_code,
            amount=amount,
        )
    except ValueError as error:
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
    print(
        f"Изменения в портфеле:\n- {code}: было {previous:.4f} → стало {new_balance:.4f}",
    )
    if estimated_value is not None:
        print(f"Оценочная выручка: {estimated_value:,.2f} USD")


def get_rate_command(from_code: str, to_code: str) -> None:
    """
    Команда get-rate:
    * принимает --from и --to;
    * проверяет коды валют и пытается взять курс из локального кеша;
    * при необходимости обновляет данные и выводит курс + метку времени.
    """
    pass
