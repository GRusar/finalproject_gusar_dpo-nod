"""Определение парсера команд ValutaTrade Hub CLI."""

from argparse import SUPPRESS, ArgumentParser


class RuArgumentParser(ArgumentParser):
    """Парсер, выводящий сообщения об ошибках и help на русском языке."""

    ERROR_REPLACEMENTS = (
        ("the following arguments are required", "требуются аргументы"),
        ("unrecognized arguments", "неизвестные аргументы"),
        ("invalid choice", "неизвестная команда"),
        ("invalid float value", "ожидается число"),
        ("invalid int value", "ожидается целое число"),
        (" (choose from ", " (доступно: "),
    )

    HELP_REPLACEMENTS = (
        ("usage:", "использование:"),
        ("options:", "опции:"),
        ("optional arguments:", "необязательные аргументы:"),
        ("positional arguments:", "позиционные аргументы:"),
    )

    def error(self, message: str) -> None:  # type: ignore[override]
        localized = message
        for english, russian in self.ERROR_REPLACEMENTS:
            localized = localized.replace(english, russian)
        raise ValueError(f"Ошибка: {localized}")

    def format_help(self) -> str:  # type: ignore[override]
        help_text = super().format_help()
        for english, russian in self.HELP_REPLACEMENTS:
            help_text = help_text.replace(english, russian)
        return help_text

    def format_usage(self) -> str:  # type: ignore[override]
        usage_text = super().format_usage()
        return usage_text.replace("usage:", "использование:")


def _add_help_argument(parser: ArgumentParser) -> None:
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=SUPPRESS,
        help="показать справку и выйти",
    )


def build_parser() -> ArgumentParser:
    """Создать парсер аргументов CLI с подкомандами."""
    parser = RuArgumentParser(prog="ValutaTradeHub", add_help=False)
    _add_help_argument(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_parser = subparsers.add_parser(
        "register",
        help="Регистрация пользователя",
        add_help=False,
        prog="ValutaTradeHub register",
    )
    _add_help_argument(register_parser)
    register_parser.add_argument("--username", required=True)
    register_parser.add_argument("--password", required=True)

    login_parser = subparsers.add_parser(
        "login",
        help="Вход в систему",
        add_help=False,
        prog="ValutaTradeHub login",
    )
    _add_help_argument(login_parser)
    login_parser.add_argument("--username", required=True)
    login_parser.add_argument("--password", required=True)

    show_parser = subparsers.add_parser(
        "show-portfolio",
        help="Показать портфель",
        add_help=False,
        prog="ValutaTradeHub show-portfolio",
    )
    _add_help_argument(show_parser)
    show_parser.add_argument("--base")

    buy_parser = subparsers.add_parser(
        "buy",
        help="Купить валюту",
        add_help=False,
        prog="ValutaTradeHub buy",
    )
    _add_help_argument(buy_parser)
    buy_parser.add_argument("--currency", required=True)
    buy_parser.add_argument("--amount", required=True, type=float)

    sell_parser = subparsers.add_parser(
        "sell",
        help="Продать валюту",
        add_help=False,
        prog="ValutaTradeHub sell",
    )
    _add_help_argument(sell_parser)
    sell_parser.add_argument("--currency", required=True)
    sell_parser.add_argument("--amount", required=True, type=float)

    rate_parser = subparsers.add_parser(
        "get-rate",
        help="Получить курс валюты",
        add_help=False,
        prog="ValutaTradeHub get-rate",
    )
    _add_help_argument(rate_parser)
    rate_parser.add_argument("--from", dest="from_code", required=True)
    rate_parser.add_argument("--to", dest="to_code", required=True)

    update_parser = subparsers.add_parser(
        "update-rates",
        help="Обновить кеш курсов",
        add_help=False,
        prog="ValutaTradeHub update-rates",
    )
    _add_help_argument(update_parser)
    update_parser.add_argument(
        "--source",
        choices=["coingecko", "exchangerate", "exchangerate-api"],
        help="Обновить только выбранный источник",
    )

    show_rates_parser = subparsers.add_parser(
        "show-rates",
        help="Показать курсы из кеша",
        add_help=False,
        prog="ValutaTradeHub show-rates",
    )
    _add_help_argument(show_rates_parser)
    show_rates_parser.add_argument(
        "--currency",
        help="Фильтр по валюте (например BTC)",
    )
    show_rates_parser.add_argument(
        "--top",
        type=int,
        help="Показать N самых дорогих криптовалют",
    )
    show_rates_parser.add_argument("--base", help="Базовая валюта для отображения")

    return parser
