"""Константы CLI ValutaTrade Hub."""

COMMANDS: dict[str, str] = {
    "register --username <имя> --password <пароль>": "Регистрация пользователя",
    "login --username <имя> --password <пароль>": "Вход в систему",
    "show-portfolio [--base BASE]": "Показать портфель",
    "buy --currency <код> --amount <число>": "Купить валюту",
    "sell --currency <код> --amount <число>": "Продать валюту",
    "get-rate --from <код> --to <код>": "Получить курс",
    "update-rates [--source coingecko|exchangerate]": "Обновить кеш курсов",
    "show-rates [--currency X --top N --base BASE]": "Показать сохранённые курсы",
    "exit": "Выход из CLI",
}

HELP_ALIGNMENT = 55
