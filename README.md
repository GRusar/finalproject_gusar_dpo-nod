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

## Установка и запуск

```bash
# Для работы с Parser Service
cp env.example .env 
# Заполнить свой ключ в файле .env

make install      # установка зависимостей
make lint         # проверка стиля (ruff)
poetry run project   # запуск CLI
# либо make project (обёртка)
```
### Установка как wheel

При установке как wheel `make package-install`
Поиск `pyproject.toml` с секцией `[tool.valutatrade]` происходит по цепочке:
Текущая директория -> переменная окружения `VALUTATRADE_PYPROJECT_PATH`

(если запускать из дирректории не содержащей `pyproject.toml` то нужно указать путь к файлу в переменной окружения `VALUTATRADE_PYPROJECT_PATH`)

```bash
export VALUTATRADE_PYPROJECT_PATH=/path/to/pyproject.toml
# можно запускать
project

# или
VALUTATRADE_PYPROJECT_PATH=/path/to/pyproject.toml project
```

## Работа с CLI

Главные команды (аргументы строго как в ТЗ):

| Команда | Назначение |
| --- | --- |
| `register --username <имя> --password <пароль>` | регистрация |
| `login --username <имя> --password <пароль>` | вход |
| `show-portfolio [--base BASE]` | показать портфель |
| `buy --currency <код> --amount <число>` | покупка валюты |
| `sell --currency <код> --amount <число>` | продажа |
| `get-rate --from <код> --to <код>` | курс одной валюты к другой |
| `update-rates [--source coingecko|exchangerate]` | обновление кеша курсов |
| `show-rates [--currency CODE] [--base BASE] [--top N]` | просмотр кеша |
| `schedule-update [--interval N --source SRC]` | периодическое обновление кеша (Ctrl+C для остановки) |
| `exit` | завершить CLI |

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
- Конвертация курсов всегда идёт через USD, но вывод и расчёты в бизнес-операциях показываются в базовой валюте из `pyproject.toml` (`DEFAULT_BASE_CURRENCY`).
- Репозиторий `valutatrade_hub/infra/repository.py` инкапсулирует загрузку/сохранение портфелей и отдаёт модели `Portfolio`/`Wallet`/`User`, так что usecases работают с моделями без прямой правки JSON.
- Планировщик `valutatrade_hub/parser_service/scheduler.py` умеет периодически запускать обновление курсов, выводит статус в консоль и завершается по Ctrl+C.
- Тестовая CLI-команда `add-usd-to-balance --amount` пополняет базовый кошелёк текущего пользователя через usecase (удобно для демонстраций/тестов).

## Пояснение реализации Singleton

- `valutatrade_hub/infra/settings.py` — `SettingsLoader` реализован через метакласс `SingletonMeta`: логика «один экземпляр» вынесена отдельно и может переиспользоваться (например, для `DatabaseManager`). Это гарантирует единственный объект вне зависимости от импортов, даёт единый источник конфигурации и позволяет безболезненно переиспользовать метакласс в других инфраструктурных компонентах.

## Asciinema
[![asciinema crud demo](https://asciinema.org/a/Qia1nmsZAIgNFKRAb1wsqHZG2.svg)](https://asciinema.org/a/Qia1nmsZAIgNFKRAb1wsqHZG2)

## Лицензия

Проект создан в рамках учебного задания Яндекс Практикума.
