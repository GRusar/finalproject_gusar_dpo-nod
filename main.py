#!/usr/bin/env python3

"""Точка входа ValutaTrade Hub CLI."""

import sys

from valutatrade_hub.cli.interface import run_cli


def main() -> None:
    """Запустить консольный интерфейс с аргументами из командной строки."""
    argv = sys.argv[1:] or None
    run_cli(argv)


if __name__ == "__main__":
    main()
