"""Бизнес-логика платформы ValutaTrade Hub."""

from __future__ import annotations

from typing import Optional


def register_user(username: str, password: str) -> None:
    """
    Команда register:
    1. Проверить уникальность username в users.json.
    2. Сгенерировать user_id (автоинкремент).
    3. Захешировать пароль с солью.
    4. Сохранить пользователя и пустой портфель.
    5. Вернуть сообщение об успехе.
    """
    pass


def login_user(username: str, password: str) -> None:
    """
    Команда login:
    1. Найти пользователя по username.
    2. Сравнить хеш пароля.
    3. Зафиксировать текущую сессию.
    """
    pass


def show_portfolio(user_id: int, base_currency: str = "USD") -> None:
    """
    Команда show-portfolio:
    1. Убедиться, что пользователь залогинен.
    2. Загрузить портфель и вывести каждый кошелёк.
    3. Рассчитать стоимость в base_currency и общую сумму.
    """
    pass


def buy_currency(user_id: int, currency_code: str, amount: float) -> None:
    """
    Команда buy:
    1. Проверить логин, код валюты и положительность amount.
    2. Создать кошелёк при его отсутствии и увеличить баланс.
    3. Опционально вывести расчётную стоимость покупки.
    """
    pass


def sell_currency(user_id: int, currency_code: str, amount: float) -> None:
    """
    Команда sell:
    1. Проверить логин и валидность данных.
    2. Убедиться в наличии кошелька и достаточном балансе.
    3. Уменьшить баланс и при необходимости отразить выручку.
    """
    pass


def get_exchange_rate(from_code: str, to_code: str) -> Optional[float]:
    """
    Команда get-rate:
    1. Проверить код валюты (верхний регистр, не пустой).
    2. Взять курс из rates.json или обновить через Parser Service.
    3. Вернуть курс и метку времени.
    """
    pass
