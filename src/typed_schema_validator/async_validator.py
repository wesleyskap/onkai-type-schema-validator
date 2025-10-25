import asyncio
import inspect
from typing import Any
from typed_schema_validator.errors import FieldError, ValidationError
from typed_schema_validator.schema import Schema
from typed_schema_validator.validator import validate as sync_validate


async def async_validate[T](
    target_type: Any,
    data: Any,
    path: str = "",
    context: dict[str, Any] | None = None,
    strict: bool = True,
) -> T:
    """
    Asynchronously validate `data` against `target_type` (supporting async custom validators).
    Raises ValidationError if data fails to match target_type or custom async validators.
    """
    ctx = context or {}

    raw_class = target_type
    if hasattr(target_type, "__origin__"):
        raw_class = target_type.__origin__

    if inspect.isclass(raw_class) and issubclass(raw_class, Schema):
        # 1. Perform base synchronous validation first (allowing async validators to be skipped until step 2)
        validated_instance = sync_validate(
            target_type,
            data,
            path=path,
            context=ctx,
            strict=strict,
            allow_async_validators=True,
        )

        # 2. Collect and run any async field validators
        field_validators = raw_class._get_field_validators()
        errors: list[FieldError] = []

        for field_name, v_funcs in field_validators.items():
            field_path = f"{path}.{field_name}" if path else field_name
            val = getattr(validated_instance, field_name, None)

            for v_func in v_funcs:
                if inspect.iscoroutinefunction(v_func):
                    try:
                        sig = inspect.signature(v_func)
                        param_names = list(sig.parameters.keys())

                        if "context" in param_names:
                            if len(param_names) >= 3 or (
                                len(param_names) == 2 and param_names[0] != "context"
                            ):
                                new_val = await v_func(
                                    raw_class, val, context=ctx
                                )
                            else:
                                new_val = await v_func(val, context=ctx)
                        elif len(param_names) >= 2:
                            new_val = await v_func(raw_class, val)
                        else:
                            new_val = await v_func(val)

                        if new_val is not None:
                            setattr(validated_instance, field_name, new_val)
                    except (ValueError, TypeError, AssertionError) as err:
                        errors.append(
                            FieldError(
                                path=field_path,
                                expected="async custom validator check",
                                actual_value=val,
                                message=str(err),
                            )
                        )

        if errors:
            raise ValidationError(errors)

        return validated_instance

    return sync_validate(
        target_type,
        data,
        path=path,
        context=ctx,
        strict=strict,
        allow_async_validators=True,
    )
