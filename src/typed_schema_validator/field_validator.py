from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class FieldValidatorMarker:
    """Marker wrapper for methods decorated with @field_validator."""

    def __init__(self, func: Callable[..., Any], fields: tuple[str, ...]) -> None:
        self.func = func
        self.fields = fields

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


def field_validator(*fields: str) -> Callable[[F], F]:
    """
    Decorator to mark a classmethod or function as a validator for specific schema fields.
    
    Example:
        class User(Schema):
            name: str
            
            @field_validator("name")
            def validate_name(cls, v: str) -> str:
                if len(v) < 2:
                    raise ValueError("Name too short")
                return v
    """

    def decorator(fn: F) -> F:
        marker = FieldValidatorMarker(fn, fields)
        return marker  # type: ignore

    return decorator
