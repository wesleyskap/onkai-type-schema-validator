import re
from typing import Any, Callable


class FieldInfo:
    """Metadata container for field constraints, defaults, and aliases."""

    def __init__(
        self,
        default: Any = ...,
        default_factory: Callable[[], Any] | None = None,
        alias: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        gt: float | int | None = None,
        ge: float | int | None = None,
        lt: float | int | None = None,
        le: float | int | None = None,
        pattern: str | re.Pattern[str] | None = None,
        description: str | None = None,
    ) -> None:
        self.default = default
        self.default_factory = default_factory
        self.alias = alias
        self.min_length = min_length
        self.max_length = max_length
        self.gt = gt
        self.ge = ge
        self.lt = lt
        self.le = le
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
        self.description = description

    def has_default(self) -> bool:
        return self.default is not ... or self.default_factory is not None

    def get_default(self) -> Any:
        if self.default_factory is not None:
            return self.default_factory()
        if self.default is not ...:
            return self.default
        return None


def Field(
    default: Any = ...,
    *,
    default_factory: Callable[[], Any] | None = None,
    alias: str | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    gt: float | int | None = None,
    ge: float | int | None = None,
    lt: float | int | None = None,
    le: float | int | None = None,
    pattern: str | re.Pattern[str] | None = None,
    description: str | None = None,
) -> Any:
    """Helper function to create a FieldInfo instance."""
    return FieldInfo(
        default=default,
        default_factory=default_factory,
        alias=alias,
        min_length=min_length,
        max_length=max_length,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        pattern=pattern,
        description=description,
    )
