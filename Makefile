.PHONY: help install project build publish package-install lint

.DEFAULT_GOAL := help

help:
		@echo "Доступные команды:"
		@echo "  make install          Устанавливает зависимости через poetry"
		@echo "  make project          Запускает игру"
		@echo "  make build            Собирает артефакты в каталог dist/"
		@echo "  make publish          Тестовая публикация пакета через poetry"
		@echo "  make package-install  Устанавливает wheel из dist/ (сначала make build)"
		@echo "  make lint             Запускает проверку Ruff"

install:
		poetry install

project:
		poetry run project

build:
		poetry build

publish:
		poetry publish --dry-run

package-install:
		python3 -m pip install dist/*.whl

lint:
		poetry run ruff check . 