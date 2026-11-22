"""Ошибки ядра. У каждой есть машинный код, его потом отдаст API в едином формате."""


class CoreError(Exception):
    code = "core_error"

    def __init__(self, message: str, **details):
        super().__init__(message)
        self.message = message
        self.details = details


class InvalidTransition(CoreError):
    code = "invalid_transition"


class UnknownCheck(CoreError):
    code = "unknown_check"


class ValidationError(CoreError):
    code = "validation_error"
