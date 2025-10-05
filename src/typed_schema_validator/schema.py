import inspect
from typing import Any, Self, get_type_hints
from typed_schema_validator.errors import FieldError, ValidationError


class Schema:
    """
    Base Schema class for creating strongly-typed models without boilerplate.
    
    Example:
        class User[T](Schema):
            id: int
            name: str
            metadata: T
            tags: list[str] = []
    """

    def __init__(self, **kwargs: Any) -> None:
        hints = self._get_resolved_annotations()
        for name in hints:
            if name in kwargs:
                setattr(self, name, kwargs[name])
            elif hasattr(self.__class__, name):
                # Class attribute default value
                setattr(self, name, getattr(self.__class__, name))

    @classmethod
    def _get_resolved_annotations(cls) -> dict[str, Any]:
        """Collect class annotations, traversing hierarchy up to Schema."""
        annotations = {}
        for base in reversed(cls.__mro__):
            if base is Schema or not issubclass(base, Schema):
                continue
            if hasattr(base, "__annotations__"):
                annotations.update(base.__annotations__)
        return annotations

    @classmethod
    def validate(cls, data: Any) -> Self:
        """Validate input dictionary/data and return an instance of this Schema."""
        from typed_schema_validator.validator import validate
        return validate(cls, data)

    def dump(self) -> dict[str, Any]:
        """Dump schema instance back to python primitives / dictionary."""
        from typed_schema_validator.serializer import dump
        return dump(self)

    def __repr__(self) -> str:
        hints = self._get_resolved_annotations()
        fields = []
        for name in hints:
            val = repr(getattr(self, name, None))
            fields.append(f"{name}={val}")
        return f"{self.__class__.__name__}({', '.join(fields)})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        hints = self._get_resolved_annotations()
        return all(getattr(self, k, None) == getattr(other, k, None) for k in hints)
