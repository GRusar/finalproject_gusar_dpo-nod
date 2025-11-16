"""Декораторы ValutaTrade Hub."""

__all__ = ["log_action", "ContextBuilder"]

from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional

from valutatrade_hub.logging_config import get_action_logger

ContextBuilder = Callable[[tuple, dict, Optional[Any], bool], Dict[str, Any]]
"""Функция, которая формирует контекст для логирования."""


def _format_value(value: Any) -> str:
    """Приводит значения к строке для лога."""
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, (int, bool)):
        return str(value)
    if value is None:
        return "None"
    return f"'{value}'"


def _compose_message(action: str, context: Dict[str, Any]) -> str:
    """Собирает финальную строку лога."""
    timestamp = datetime.now(timezone.utc).isoformat()
    action_part = action.upper()
    parts = [f"{key}={_format_value(val)}" for key, val in context.items()]
    return " ".join([timestamp, action_part, *parts])


def log_action(
    action: str,
    *,
    context_getter: Optional[ContextBuilder] = None,
    verbose: bool = False,
) -> Callable:
    """Декоратор для логирования buy/sell и других операций."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_action_logger()

            def build_context(result: Optional[Any]) -> Dict[str, Any]:
                if not context_getter:
                    return {}
                try:
                    return context_getter(args, kwargs, result, verbose)
                except Exception:
                    return {}

            try:
                result = func(*args, **kwargs)
            except Exception as error:
                context = {"result": "ERROR", "error_type": error.__class__.__name__}
                if str(error):
                    context["error_message"] = str(error)
                context.update(build_context(None))
                logger.info(_compose_message(action, context))
                raise
            else:
                context = {"result": "OK"}
                context.update(build_context(result))
                logger.info(_compose_message(action, context))
                return result

        return wrapper

    return decorator
