"""Вспомогательные функции для core-модуля."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    """Парсит ISO-дату и возвращает aware datetime (или None)."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def normalize_currency_code(code: str) -> str:
    """Нормализация кода валюты в верхний регистр без пробелов."""
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Код валюты должен быть непустой строкой")
    normalized = code.strip().upper()
    if " " in normalized or not 2 <= len(normalized) <= 5:
        raise ValueError("Код валюты должен быть 2-5 символов без пробелов")
    return normalized


def validate_positive_amount(amount: Any) -> float:
    """Проверяет, что сумма положительная, и возвращает float."""
    try:
        value = float(amount)
    except (TypeError, ValueError) as exc:
        raise ValueError("Сумма должна быть числом") from exc
    if value <= 0:
        raise ValueError("Сумма должна быть положительной")
    return value
