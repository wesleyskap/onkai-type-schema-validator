from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class FieldSerializerMarker:
    """Marker wrapper for methods decorated with @field_serializer."""

    def __init__(self, func: Callable[..., Any], fields: tuple[str, ...]) -> None:
        self.func = func
        self.fields = fields

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


def field_serializer(*fields: str) -> Callable[[F], F]:
    """
    Decorator to mark a classmethod or function as a custom serializer for specific schema fields.
    
    Example:
        class Event(Schema):
            created_at: datetime
            
            @field_serializer("created_at")
            def serialize_created_at(cls, v: datetime) -> str:
                return v.strftime("%Y-%m-%d")
    """

    def decorator(fn: F) -> F:
        marker = FieldSerializerMarker(fn, fields)
        return marker  # type: ignore

    return decorator
