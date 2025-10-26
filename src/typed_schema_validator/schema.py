import functools
import inspect
from typing import Any, Callable, Self
from typed_schema_validator.field import FieldInfo
from typed_schema_validator.field_serializer import FieldSerializerMarker
from typed_schema_validator.field_validator import FieldValidatorMarker
from typed_schema_validator.model_validator import ModelValidatorMarker


class Schema:
    """
    Base Schema class for creating strongly-typed models with constraint, validation,
    aliases, extra field policies, frozen immutability, cached reflection, model copy,
    model-level validators, validation context, async validation, and JSON Schema generation capabilities.
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
            field_info: FieldInfo | None = None
            if hasattr(self.__class__, name):
                attr_val = getattr(self.__class__, name)
                if isinstance(attr_val, FieldInfo):
                    field_info = attr_val

            alias_name = field_info.alias if field_info and field_info.alias else name

            if name in kwargs:
                super().__setattr__(name, kwargs[name])
            elif alias_name in kwargs:
                super().__setattr__(name, kwargs[alias_name])
            elif field_info is not None and field_info.has_default():
                super().__setattr__(name, field_info.get_default())
            elif hasattr(self.__class__, name) and not isinstance(
                getattr(self.__class__, name), FieldInfo
            ):
                super().__setattr__(name, getattr(self.__class__, name))

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

    def copy(self, update: dict[str, Any] | None = None) -> Self:
        """
        Create a copy of this Schema instance with optional field overrides in `update`.
        Works for both mutable and frozen schemas.
        """
        hints = self._get_resolved_annotations()
        data = {}
        for k in hints:
            data[k] = getattr(self, k, None)
        if update:
            data.update(update)
        return self.__class__(**data)

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
                values.append((k, str(val)))
            else:
                values.append((k, val))
        return hash((self.__class__.__name__, tuple(values)))

    @classmethod
    @functools.lru_cache(maxsize=1024)
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
    @functools.lru_cache(maxsize=1024)
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
    @functools.lru_cache(maxsize=1024)
    def _get_model_validators(
        cls,
    ) -> dict[str, list[Callable[..., Any]]]:
        """Collect @model_validator methods defined across class hierarchy."""
        validators: dict[str, list[Callable[..., Any]]] = {
            "before": [],
            "after": [],
        }
        for base in reversed(cls.__mro__):
            if base is Schema or not issubclass(base, Schema):
                continue
            for name, attr in base.__dict__.items():
                if isinstance(attr, ModelValidatorMarker):
                    func = attr.func
                    if isinstance(func, (classmethod, staticmethod)):
                        func = func.__func__
                    validators[attr.mode].append(func)
                elif hasattr(attr, "__func__"):
                    raw_func = getattr(attr, "__func__")
                    if isinstance(raw_func, ModelValidatorMarker):
                        validators[raw_func.mode].append(raw_func.func)
        return validators

    @classmethod
    @functools.lru_cache(maxsize=1024)
    def _get_field_serializers(cls) -> dict[str, list[Callable[..., Any]]]:
        """Collect @field_serializer methods defined across class hierarchy."""
        serializers: dict[str, list[Callable[..., Any]]] = {}
        for base in reversed(cls.__mro__):
            if base is Schema or not issubclass(base, Schema):
                continue
            for name, attr in base.__dict__.items():
                if isinstance(attr, FieldSerializerMarker):
                    func = attr.func
                    if isinstance(func, (classmethod, staticmethod)):
                        func = func.__func__
                    for field_name in attr.fields:
                        serializers.setdefault(field_name, []).append(func)
                elif hasattr(attr, "__func__"):
                    raw_func = getattr(attr, "__func__")
                    if isinstance(raw_func, FieldSerializerMarker):
                        for field_name in raw_func.fields:
                            serializers.setdefault(field_name, []).append(raw_func.func)
        return serializers

    @classmethod
    def validate(
        cls,
        data: Any,
        context: dict[str, Any] | None = None,
        strict: bool = True,
    ) -> Self:
        """Validate input dictionary/data and return an instance of this Schema."""
        from typed_schema_validator.validator import validate as core_validate
        return core_validate(cls, data, context=context, strict=strict)

    @classmethod
    async def async_validate(
        cls,
        data: Any,
        context: dict[str, Any] | None = None,
        strict: bool = True,
    ) -> Self:
        """Asynchronously validate input dictionary/data supporting async custom validators."""
        from typed_schema_validator.async_validator import async_validate as core_async_validate
        return await core_async_validate(cls, data, context=context, strict=strict)

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        """Generate JSON Schema dictionary for this Schema model."""
        from typed_schema_validator.json_schema import to_json_schema
        return to_json_schema(cls)

    def dump(self, by_alias: bool = False) -> dict[str, Any]:
        """Dump schema instance back to python primitives / dictionary."""
        from typed_schema_validator.serializer import dump as core_dump
        return core_dump(self, by_alias=by_alias)

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
