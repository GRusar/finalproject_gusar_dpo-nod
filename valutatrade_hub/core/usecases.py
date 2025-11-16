"""Бизнес-логика платформы ValutaTrade Hub."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from valutatrade_hub.core.models import User

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def register_user(username: str, password: str) -> int:
    """
    Команда register:
    1. Проверить уникальность username в users.json.
    2. Сгенерировать user_id (автоинкремент).
    3. Захешировать пароль с солью.
    4. Сохранить пользователя и пустой портфель.
    5. Вернуть сообщение об успехе.
    """
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

    return new_user_id


def login_user(username: str, password: str) -> int:
    """
    Команда login:
    1. Найти пользователя по username.
    2. Сравнить хеш пароля.
    3. Зафиксировать текущую сессию.
    """
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

    return user.user_id


def show_portfolio(user_id: int, base_currency: str = "USD") -> dict[str, Any]:
    """
    Команда show-portfolio:
    1. Убедиться, что пользователь залогинен.
    2. Загрузить портфель и вывести каждый кошелёк.
    3. Рассчитать стоимость в base_currency и общую сумму.
    """
    raise NotImplementedError


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
