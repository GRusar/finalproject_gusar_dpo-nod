"""Пользовательские исключения ValutaTrade Hub."""


class InsufficientFundsError(Exception):
    """Недостаточно средств на кошельке для завершения операции."""

    def __init__(self, *, available: float, required: float, code: str) -> None:
        message = (
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )
        super().__init__(message)
        self.available = available
        self.required = required
        self.code = code


class CurrencyNotFoundError(Exception):
    """Неизвестная валюта по заданному коду."""

    def __init__(self, code: str) -> None:
        message = f"Неизвестная валюта '{code}'"
        super().__init__(message)
        self.code = code


class ApiRequestError(Exception):
    """Ошибки обращения к внешним API (rates/parsers и т.д.)."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
        self.reason = reason
