from dataclasses import dataclass
from typing import Any


@dataclass
class FieldError:
    """Represents a validation error for a specific field or element path."""
    path: str
    expected: str
    actual_value: Any
    message: str

    def __str__(self) -> str:
        loc = f" at '{self.path}'" if self.path else ""
        return f"Invalid value{loc}: expected {self.expected}, got {type(self.actual_value).__name__} ({self.message})"


class ValidationError(Exception):
    """Exception raised when validation fails for one or more fields."""

    def __init__(self, errors: list[FieldError]) -> None:
        self.errors = errors
        error_summary = "\n".join(f"  - {err}" for err in errors)
        super().__init__(f"Validation failed with {len(errors)} error(s):\n{error_summary}")
