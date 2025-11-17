# Init

## Features

- `valutatrade_hub/cli/command_parser.py` — CLI использует `argparse` с русифицированными ошибками и удобным help по командам.
- `valutatrade_hub/parser_service/config.py` — Parser Service проверяет переменную окружения `EXCHANGERATE_API_KEY` и, если её нет, пытается прочитать ключ из `.env`; при отсутствии ключа явно сообщает об ошибке.

## Пояснение реализации Singleton

- `valutatrade_hub/infra/settings.py` — `SettingsLoader` реализован через метакласс `SingletonMeta`: логика «один экземпляр» вынесена отдельно и может переиспользоваться (например, для `DatabaseManager`). Это гарантирует единственный объект вне зависимости от импортов и упрощает поддержание конфигурации.

### Конфигурация в `[tool.valutatrade]`

`SettingsLoader` берёт значения из `pyproject.toml` в секции `[tool.valutatrade]`:

- `data_dir` — базовая директория хранилища;
- `users_file`, `portfolios_file`, `rates_file` — конкретные json-файлы для данных;
- `rates_ttl_seconds` — время «протухания» курсов;
- `default_base_currency` — валюта по умолчанию для конвертации;
- `log_path` — файл логов (для будущего декоратора `@log_action`).

Секция обязательна: если её нет или отсутствуют ключи, `SettingsLoader` сразу сообщает об этом и приложение не стартует с неопределённой конфигурацией.
