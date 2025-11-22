# ValutaTrade Hub

CLI-приложение для учёта пользовательских портфелей и операций с валютой. Основные сценарии: регистрация/логин, покупка и продажа активов, просмотр портфеля с пересчётом по актуальному курсу, обновление кеша курсов из Parser Service.

## Структура проекта

- `valutatrade_hub/core` — доменные модели (`User`, `Wallet`, `Portfolio`) и usecase-слой.
- `valutatrade_hub/cli` — парсер команд и обработчики CLI.
- `valutatrade_hub/infra` — `SettingsLoader`, `DatabaseManager`, базовая инфраструктура.
- `valutatrade_hub/parser_service` — конфигурация, API-клиенты, сторедж и обновление курсов.
- `valutatrade_hub/logging_config.py`, `valutatrade_hub/decorators.py` — настройка логов и декораторы действий.
- `data/` — `users.json`, `portfolios.json`, `rates.json`, `exchange_rates.json`.
- `logs/` — `actions.log`, `parser.log` (ротация файлов включена).

## Требования

- Python 3.12+
- Poetry
- Опционально `.env` с `EXCHANGERATE_API_KEY`, или переменная окружения (для Parser Service).

## Установка и запуск

```bash
cp env.example .env

make install      # установка зависимостей
make lint         # проверка стиля (ruff)
poetry run project   # запуск CLI
# либо make project (обёртка)
```
## Установка как wheel

После `make package-install` (установки как wheel) нужно указать путь к pyproject с секцией `[tool.valutatrade]` (см. [конфигурация](#конфигурация-toolvalutatrade)) в переменной окружения `VALUTATRADE_PYPROJECT_PATH`

```bash
export VALUTATRADE_PYPROJECT_PATH=/path/to/pyproject.toml
# можно запускать
project
```

## Конфигурация `[tool.valutatrade]`

`SettingsLoader` читает обязательные ключи из `pyproject.toml`:

- `users_file`, `portfolios_file`, `rates_file` — JSON-файлы данных;
- `rates_ttl_seconds` — TTL кеша курсов;
- `default_base_currency` — валюта пересчёта по умолчанию;
- `log_path`, `parser_log_path` — файлы журналов.

### Ключ внешнего API

Parser Service использует `EXCHANGERATE_API_KEY`. Логика такая:

1. Берём переменную окружения.
2. Если нет, ищем `.env` в корне проекта.
3. Если ключ не найден — `update-rates` сообщает об ошибке и ничего не трогает.

## Работа с CLI

Главные команды (аргументы строго как в ТЗ):

| Команда | Назначение |
| --- | --- |
| `register --username <имя> --password <пароль>` | регистрация |
| `login --username <имя> --password <пароль>` | вход |
| `show-portfolio [--base USD]` | показать портфель |
| `buy --currency <код> --amount <число>` | покупка валюты |
| `sell --currency <код> --amount <число>` | продажа |
| `get-rate --from <код> --to <код>` | курс одной валюты к другой |
| `update-rates [--source coingecko|exchangerate]` | обновление кеша курсов |
| `show-rates [--currency CODE] [--base USD] [--top N]` | просмотр кеша |
| `exit` | завершить CLI |

Пример сценария:

```bash
$ poetry run project register --username alice --password secret
$ poetry run project login --username alice --password secret
$ poetry run project buy --currency BTC --amount 0.05
$ poetry run project show-portfolio --base USD
$ poetry run project get-rate --from BTC --to EUR
```

Интерактивный режим:

```bash
$ poetry run project
ValutaTrade Hub CLI.
> register --username bob --password 1234
> login --username bob --password 1234
> buy --currency ETH --amount 0.5
> show-portfolio
> exit
```

Ошибки печатаются по-русски (например, «Недостаточно средств», «Неизвестная валюта»), поддерживается вывод подсказок `команда -h`.

## Кеш курсов и Parser Service

- `update-rates` опрашивает CoinGecko и ExchangeRate-API, объединяет пары, сохраняет `data/rates.json` и дописывает историю в `data/exchange_rates.json`.
- При частичном успехе ошибки выводятся в CLI и лог `logs/parser.log`.
- Кеш хранит поле `last_refresh`. Любая операция с портфелем проверяет TTL (`rates_ttl_seconds`): если курсы устарели или файла нет, пользователю предлагается сначала обновить данные.
- `show-rates` помогает проверить содержимое кеша без операций над портфелем.

## Features

- `valutatrade_hub/cli/command_parser.py` — CLI использует `argparse` с русифицированными ошибками, автогенерируемым help и uniform командами.
- `valutatrade_hub/parser_service/config.py` — Parser Service проверяет переменную окружения `EXCHANGERATE_API_KEY` и, если её нет, пытается прочитать ключ из `.env`; при отсутствии ключа явно сообщает об ошибке. При загрузке ключ очищается от пробелов, чтобы избежать случайных опечаток.
- Конфигурация логирования вынесена в `logging_config.py`: действия пользователей (`log_action`) и Parser Service пишут в отдельные файлы с ротацией, формат русскоязычный.

## Пояснение реализации Singleton

- `valutatrade_hub/infra/settings.py` — `SettingsLoader` реализован через метакласс `SingletonMeta`: логика «один экземпляр» вынесена отдельно и может переиспользоваться (например, для `DatabaseManager`). Это гарантирует единственный объект вне зависимости от импортов, даёт единый источник конфигурации и позволяет безболезненно переиспользовать метакласс в других инфраструктурных компонентах.


## Лицензия

Проект создан в рамках учебного задания Яндекс Практикума.
