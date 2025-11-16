"""Константы CLI ValutaTrade Hub."""

COMMANDS: dict[str, str] = {
    "register --username <имя> --password <пароль>": "Регистрация пользователя",
    "login --username <имя> --password <пароль>": "Вход в систему",
    "show-portfolio [--base USD]": "Показать портфель",
    "buy --currency <код> --amount <число>": "Купить валюту",
    "sell --currency <код> --amount <число>": "Продать валюту",
    "get-rate --from <код> --to <код>": "Получить курс",
    "exit": "Выход из CLI",
}

HELP_ALIGNMENT = 55
