import inspect
from typing import Any, Callable, Self
from typed_schema_validator.field import FieldInfo
from typed_schema_validator.field_validator import FieldValidatorMarker


class Schema:
    """
    Base Schema class for creating strongly-typed models with constraint, validation,
    extra field policies, frozen immutability, and JSON Schema generation capabilities.
    """

    extra: str = "ignore"  # Options: "ignore", "forbid"
    frozen: bool = False

    def __init_subclass__(
        cls, extra: str = "ignore", frozen: bool = False, **kwargs: Any
    ) -> None:
        super().__init_subclass__(**kwargs)
        cls.extra = extra
        cls.frozen = frozen

    def __init__(self, **kwargs: Any) -> None:
        hints = self._get_resolved_annotations()
        for name in hints:
            if name in kwargs:
                super().__setattr__(name, kwargs[name])
            elif hasattr(self.__class__, name):
                attr_val = getattr(self.__class__, name)
                if isinstance(attr_val, FieldInfo):
                    if attr_val.has_default():
                        super().__setattr__(name, attr_val.get_default())
                else:
                    super().__setattr__(name, attr_val)

        super().__setattr__("_initialized", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_initialized", False) and getattr(self, "frozen", False):
            raise TypeError(
                f"Cannot mutate field '{name}' on frozen schema '{self.__class__.__name__}'"
            )
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        if getattr(self, "_initialized", False) and getattr(self, "frozen", False):
            raise TypeError(
                f"Cannot delete field '{name}' on frozen schema '{self.__class__.__name__}'"
            )
        super().__delattr__(name)

    def __hash__(self) -> int:
        if not getattr(self, "frozen", False):
            raise TypeError(
                f"Unhashable type: '{self.__class__.__name__}' schema is not frozen"
            )
        hints = self._get_resolved_annotations()
        values = []
        for k in hints:
            val = getattr(self, k, None)
            if isinstance(val, (list, dict, set)):
                # Convert unhashable containers for hash computation
                values.append((k, str(val)))
            else:
                values.append((k, val))
        return hash((self.__class__.__name__, tuple(values)))

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
    def _get_field_validators(cls) -> dict[str, list[Callable[..., Any]]]:
        """Collect @field_validator methods defined across class hierarchy."""
        validators: dict[str, list[Callable[..., Any]]] = {}
        for base in reversed(cls.__mro__):
            if base is Schema or not issubclass(base, Schema):
                continue
            for name, attr in base.__dict__.items():
                if isinstance(attr, FieldValidatorMarker):
                    func = attr.func
                    if isinstance(func, (classmethod, staticmethod)):
                        func = func.__func__
                    for field_name in attr.fields:
                        validators.setdefault(field_name, []).append(func)
                elif hasattr(attr, "__func__"):
                    raw_func = getattr(attr, "__func__")
                    if isinstance(raw_func, FieldValidatorMarker):
                        for field_name in raw_func.fields:
                            validators.setdefault(field_name, []).append(raw_func.func)
        return validators

    @classmethod
    def validate(cls, data: Any) -> Self:
        """Validate input dictionary/data and return an instance of this Schema."""
        from typed_schema_validator.validator import validate as core_validate
        return core_validate(cls, data)

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        """Generate JSON Schema dictionary for this Schema model."""
        from typed_schema_validator.json_schema import to_json_schema
        return to_json_schema(cls)

    def dump(self) -> dict[str, Any]:
        """Dump schema instance back to python primitives / dictionary."""
        from typed_schema_validator.serializer import dump as core_dump
        return core_dump(self)

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
