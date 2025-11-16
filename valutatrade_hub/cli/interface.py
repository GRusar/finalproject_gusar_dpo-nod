
"""Командный интерфейс ValutaTrade Hub."""

from valutatrade_hub.core import usecases


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

    print(f"Вы вошли как '{normalized_username}' (id={user_id})")


def show_portfolio_command(base_currency: str = "USD") -> None:
    """
    Команда show-portfolio:
    * доступна только залогиненному пользователю;
    * выводит все кошельки и стоимость в базовой валюте (по умолчанию USD);
    * принимает опциональный --base.
    """
    pass


def buy_command(currency_code: str, amount: float) -> None:
    """
    Команда buy:
    * требует логина;
    * проверяет --currency и положительный --amount;
    * создаёт кошелёк при необходимости и увеличивает баланс.
    """
    pass


def sell_command(currency_code: str, amount: float) -> None:
    """
    Команда sell:
    * требует логина;
    * проверяет существование кошелька и достаточно ли средств;
    * уменьшает баланс и может показывать оценочную выручку.
    """
    pass


def get_rate_command(from_code: str, to_code: str) -> None:
    """
    Команда get-rate:
    * принимает --from и --to;
    * проверяет коды валют и пытается взять курс из локального кеша;
    * при необходимости обновляет данные и выводит курс + метку времени.
    """
    pass
