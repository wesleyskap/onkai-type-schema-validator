import dataclasses
import enum
import functools
import inspect
import types
import typing
from typing import Any, Literal, get_args, get_origin, get_type_hints, is_typeddict

from typed_schema_validator.errors import FieldError, ValidationError
from typed_schema_validator.field import FieldInfo
from typed_schema_validator.schema import Schema
from typed_schema_validator.type_inspector import (
    build_type_var_map,
    get_union_args,
    is_optional_type,
    is_pep695_alias,
    is_union_type,
    substitute_typevars,
)


@functools.lru_cache(maxsize=1024)
def _get_schema_field_info_map(raw_class: type) -> tuple[dict[str, FieldInfo], set[str]]:
    field_info_map: dict[str, FieldInfo] = {}
    mapped_input_keys: set[str] = set()

    if hasattr(raw_class, "_get_resolved_annotations"):
        annotations = raw_class._get_resolved_annotations()
        for fn in annotations:
            f_info: FieldInfo | None = None
            if hasattr(raw_class, fn):
                class_attr = getattr(raw_class, fn)
                if isinstance(class_attr, FieldInfo):
                    f_info = class_attr

            if f_info is not None:
                field_info_map[fn] = f_info
                if f_info.alias:
                    mapped_input_keys.add(f_info.alias)
            mapped_input_keys.add(fn)

    return field_info_map, mapped_input_keys


def validate[T](
    target_type: Any,
    data: Any,
    path: str = "",
    context: dict[str, Any] | None = None,
    strict: bool = True,
    allow_async_validators: bool = False,
) -> T:
    """
    Validate `data` against `target_type` (including PEP 695 generics, dataclasses, typeddicts, unions, schemas).
    Supports optional `context` dictionary for custom validators and `strict` mode flag.
    Raises ValidationError if data fails to match target_type or field constraints.
    """
    errors: list[FieldError] = []
    result = _validate_internal(
        target_type,
        data,
        path,
        errors,
        type_var_map={},
        context=context or {},
        strict=strict,
        allow_async_validators=allow_async_validators,
    )
    if errors:
        raise ValidationError(errors)
    return result


def _check_field_constraints(
    field_info: FieldInfo, val: Any, path: str, errors: list[FieldError]
) -> None:
    """Validate value against FieldInfo constraint parameters."""
    if val is None:
        return

    if hasattr(val, "__len__"):
        length = len(val)
        if field_info.min_length is not None and length < field_info.min_length:
            errors.append(
                FieldError(
                    path=path,
                    expected=f"min_length={field_info.min_length}",
                    actual_value=val,
                    message=f"Length {length} is less than minimum required length {field_info.min_length}",
                )
            )
        if field_info.max_length is not None and length > field_info.max_length:
            errors.append(
                FieldError(
                    path=path,
                    expected=f"max_length={field_info.max_length}",
                    actual_value=val,
                    message=f"Length {length} exceeds maximum allowed length {field_info.max_length}",
                )
            )

    if isinstance(val, (int, float)) and not isinstance(val, bool):
        if field_info.gt is not None and val <= field_info.gt:
            errors.append(
                FieldError(
                    path=path,
                    expected=f">{field_info.gt}",
                    actual_value=val,
                    message=f"Value {val} must be strictly greater than {field_info.gt}",
                )
            )
        if field_info.ge is not None and val < field_info.ge:
            errors.append(
                FieldError(
                    path=path,
                    expected=f">={field_info.ge}",
                    actual_value=val,
                    message=f"Value {val} must be greater than or equal to {field_info.ge}",
                )
            )
        if field_info.lt is not None and val >= field_info.lt:
            errors.append(
                FieldError(
                    path=path,
                    expected=f"<{field_info.lt}",
                    actual_value=val,
                    message=f"Value {val} must be strictly less than {field_info.lt}",
                )
            )
        if field_info.le is not None and val > field_info.le:
            errors.append(
                FieldError(
                    path=path,
                    expected=f"<={field_info.le}",
                    actual_value=val,
                    message=f"Value {val} must be less than or equal to {field_info.le}",
                )
            )

    if field_info.pattern is not None and isinstance(val, str):
        if not field_info.pattern.search(val):
            errors.append(
                FieldError(
                    path=path,
                    expected=f"pattern '{field_info.pattern.pattern}'",
                    actual_value=val,
                    message=f"String '{val}' does not match pattern '{field_info.pattern.pattern}'",
                )
            )


def _validate_internal(
    target_type: Any,
    data: Any,
    path: str,
    errors: list[FieldError],
    type_var_map: dict[Any, Any],
    context: dict[str, Any],
    strict: bool,
    allow_async_validators: bool = False,
) -> Any:
    # 1. Build type var mapping from specialized generic / alias args
    base_origin, new_type_var_map = build_type_var_map(target_type)
    merged_map = {**type_var_map, **new_type_var_map}

    # 2. Resolve PEP 695 TypeAliasType
    if is_pep695_alias(target_type):
        target_type = target_type.__value__
    elif is_pep695_alias(base_origin):
        target_type = base_origin.__value__

    # 3. Substitute active TypeVars
    target_type = substitute_typevars(target_type, merged_map)

    # 4. Any / object type bypass
    if target_type is Any or target_type is object:
        return data

    base_origin, extra_type_var_map = build_type_var_map(target_type)
    merged_map.update(extra_type_var_map)

    # 5. Union Types
    if is_union_type(target_type):
        union_args = get_union_args(target_type)
        if data is None and type(None) in union_args:
            return None

        for variant in union_args:
            if variant is type(None) and data is not None:
                continue
            sub_errors: list[FieldError] = []
            res = _validate_internal(
                variant,
                data,
                path,
                sub_errors,
                merged_map,
                context,
                strict,
                allow_async_validators,
            )
            if not sub_errors:
                return res

        expected_str = " | ".join(
            getattr(arg, "__name__", str(arg)) for arg in union_args
        )
        errors.append(
            FieldError(
                path=path,
                expected=expected_str,
                actual_value=data,
                message=f"Value '{data}' does not match any type in union ({expected_str})",
            )
        )
        return None

    # 6. Literal Types
    if get_origin(target_type) is Literal:
        allowed = get_args(target_type)
        if data not in allowed:
            errors.append(
                FieldError(
                    path=path,
                    expected=f"Literal{allowed}",
                    actual_value=data,
                    message=f"Expected one of {allowed}, got {data}",
                )
            )
            return None
        return data

    # 7. Enum Types
    if isinstance(target_type, type) and issubclass(target_type, enum.Enum):
        try:
            return target_type(data)
        except ValueError:
            valid_vals = [e.value for e in target_type]
            errors.append(
                FieldError(
                    path=path,
                    expected=f"Enum {target_type.__name__} values {valid_vals}",
                    actual_value=data,
                    message=f"Invalid enum value '{data}' for {target_type.__name__}",
                )
            )
            return None

    # 8. TypedDict Validation
    raw_class = base_origin if inspect.isclass(base_origin) else target_type
    if inspect.isclass(raw_class) and is_typeddict(raw_class):
        if not isinstance(data, dict):
            errors.append(
                FieldError(
                    path=path,
                    expected=f"TypedDict '{raw_class.__name__}'",
                    actual_value=data,
                    message=f"Expected dict for TypedDict '{raw_class.__name__}', got {type(data).__name__}",
                )
            )
            return None

        annotations = get_type_hints(raw_class, include_extras=True)
        required_keys = getattr(raw_class, "__required_keys__", set(annotations.keys()))
        validated_dict = {}

        for key, raw_field_type in annotations.items():
            key_path = f"{path}.{key}" if path else key
            effective_type = substitute_typevars(raw_field_type, merged_map)

            field_origin = get_origin(effective_type)
            if field_origin is typing.Required:
                effective_type = get_args(effective_type)[0]
                is_req = True
            elif field_origin is typing.NotRequired:
                effective_type = get_args(effective_type)[0]
                is_req = False
            else:
                is_req = key in required_keys

            if key in data:
                val = data[key]
                validated_val = _validate_internal(
                    effective_type,
                    val,
                    key_path,
                    errors,
                    merged_map,
                    context,
                    strict,
                    allow_async_validators,
                )
                validated_dict[key] = validated_val
            elif is_req:
                errors.append(
                    FieldError(
                        path=key_path,
                        expected=getattr(effective_type, "__name__", str(effective_type)),
                        actual_value=None,
                        message=f"Missing required TypedDict key '{key}'",
                    )
                )

        return validated_dict

    # 9. Standard Dataclass Validation
    if inspect.isclass(raw_class) and dataclasses.is_dataclass(raw_class):
        if not isinstance(data, dict):
            errors.append(
                FieldError(
                    path=path,
                    expected=f"Dataclass '{raw_class.__name__}'",
                    actual_value=data,
                    message=f"Expected dict for Dataclass '{raw_class.__name__}', got {type(data).__name__}",
                )
            )
            return None

        dc_fields = {f.name: f for f in dataclasses.fields(raw_class)}
        kwargs = {}

        for f_name, f_obj in dc_fields.items():
            field_path = f"{path}.{f_name}" if path else f_name
            effective_type = substitute_typevars(f_obj.type, merged_map)

            if f_name in data:
                val = data[f_name]
                validated_val = _validate_internal(
                    effective_type,
                    val,
                    field_path,
                    errors,
                    merged_map,
                    context,
                    strict,
                    allow_async_validators,
                )
                kwargs[f_name] = validated_val
            elif f_obj.default is not dataclasses.MISSING:
                kwargs[f_name] = f_obj.default
            elif f_obj.default_factory is not dataclasses.MISSING:
                kwargs[f_name] = f_obj.default_factory()
            elif is_optional_type(effective_type):
                kwargs[f_name] = None
            else:
                errors.append(
                    FieldError(
                        path=field_path,
                        expected=getattr(effective_type, "__name__", str(effective_type)),
                        actual_value=None,
                        message=f"Missing required dataclass field '{f_name}'",
                    )
                )

        return raw_class(**kwargs)

    # 10. Container Origin Types (list, dict, set, tuple)
    origin = base_origin if base_origin is not target_type else get_origin(target_type)
    if origin is not None:
        args = get_args(target_type)

        if origin is list or origin is typing.List:
            if not isinstance(data, list):
                errors.append(
                    FieldError(
                        path=path,
                        expected="list",
                        actual_value=data,
                        message=f"Expected list, got {type(data).__name__}",
                    )
                )
                return None
            item_type = args[0] if args else Any
            validated_list = []
            for idx, item in enumerate(data):
                item_path = f"{path}[{idx}]" if path else f"[{idx}]"
                validated_item = _validate_internal(
                    item_type,
                    item,
                    item_path,
                    errors,
                    merged_map,
                    context,
                    strict,
                    allow_async_validators,
                )
                validated_list.append(validated_item)
            return validated_list

        if origin is dict or origin is typing.Dict:
            if not isinstance(data, dict):
                errors.append(
                    FieldError(
                        path=path,
                        expected="dict",
                        actual_value=data,
                        message=f"Expected dict, got {type(data).__name__}",
                    )
                )
                return None
            key_type = args[0] if len(args) > 0 else Any
            val_type = args[1] if len(args) > 1 else Any
            validated_dict = {}
            for k, v in data.items():
                key_path = f"{path}.<key:{k}>" if path else f"<key:{k}>"
                val_path = f"{path}.{k}" if path else str(k)
                vk = _validate_internal(
                    key_type,
                    k,
                    key_path,
                    errors,
                    merged_map,
                    context,
                    strict,
                    allow_async_validators,
                )
                vv = _validate_internal(
                    val_type,
                    v,
                    val_path,
                    errors,
                    merged_map,
                    context,
                    strict,
                    allow_async_validators,
                )
                validated_dict[vk] = vv
            return validated_dict

        if origin is set or origin is typing.Set:
            if not isinstance(data, (set, list, tuple)):
                errors.append(
                    FieldError(
                        path=path,
                        expected="set",
                        actual_value=data,
                        message=f"Expected set/iterable, got {type(data).__name__}",
                    )
                )
                return None
            item_type = args[0] if args else Any
            validated_set = set()
            for idx, item in enumerate(data):
                item_path = f"{path}{{{idx}}}" if path else f"{{{idx}}}"
                validated_set.add(
                    _validate_internal(
                        item_type,
                        item,
                        item_path,
                        errors,
                        merged_map,
                        context,
                        strict,
                        allow_async_validators,
                    )
                )
            return validated_set

        if origin is tuple or origin is typing.Tuple:
            if not isinstance(data, (tuple, list)):
                errors.append(
                    FieldError(
                        path=path,
                        expected="tuple",
                        actual_value=data,
                        message=f"Expected tuple, got {type(data).__name__}",
                    )
                )
                return None
            if args:
                if len(args) == 2 and args[1] is ...:
                    item_type = args[0]
                    validated_tuple = tuple(
                        _validate_internal(
                            item_type,
                            item,
                            f"{path}[{i}]" if path else f"[{i}]",
                            errors,
                            merged_map,
                            context,
                            strict,
                            allow_async_validators,
                        )
                        for i, item in enumerate(data)
                    )
                    return validated_tuple
                else:
                    if len(data) != len(args):
                        errors.append(
                            FieldError(
                                path=path,
                                expected=f"tuple of length {len(args)}",
                                actual_value=data,
                                message=f"Expected tuple of length {len(args)}, got length {len(data)}",
                            )
                        )
                        return None
                    validated_tuple = tuple(
                        _validate_internal(
                            args[i],
                            item,
                            f"{path}[{i}]" if path else f"[{i}]",
                            errors,
                            merged_map,
                            context,
                            strict,
                            allow_async_validators,
                        )
                        for i, item in enumerate(data)
                    )
                    return validated_tuple

    # 11. Schema Subclass Validation
    if inspect.isclass(raw_class) and issubclass(raw_class, Schema):
        if not isinstance(data, dict):
            errors.append(
                FieldError(
                    path=path,
                    expected=raw_class.__name__,
                    actual_value=data,
                    message=f"Expected dict input for Schema '{raw_class.__name__}', got {type(data).__name__}",
                )
            )
            return None

        # Run @model_validator(mode="before")
        model_validators = raw_class._get_model_validators()
        for mv in model_validators.get("before", []):
            try:
                sig = inspect.signature(mv)
                params_count = len(sig.parameters)
                if params_count >= 2:
                    data = mv(raw_class, data)
                else:
                    data = mv(data)
            except (ValueError, TypeError, AssertionError) as err:
                errors.append(
                    FieldError(
                        path=path,
                        expected="model validator before check",
                        actual_value=data,
                        message=str(err),
                    )
                )

        annotations = raw_class._get_resolved_annotations()
        custom_validators = raw_class._get_field_validators()
        extra_policy = getattr(raw_class, "extra", "ignore")

        field_info_map, mapped_input_keys = _get_schema_field_info_map(raw_class)

        # Forbid extra fields check
        if extra_policy == "forbid":
            for data_key in data:
                if data_key not in mapped_input_keys:
                    extra_path = f"{path}.{data_key}" if path else data_key
                    errors.append(
                        FieldError(
                            path=extra_path,
                            expected="no extra fields",
                            actual_value=data[data_key],
                            message=f"Unexpected extra field '{data_key}'",
                        )
                    )

        kwargs = {}

        for field_name, field_type in annotations.items():
            field_path = f"{path}.{field_name}" if path else field_name
            effective_type = substitute_typevars(field_type, merged_map)
            field_info = field_info_map.get(field_name)
            alias_key = field_info.alias if field_info and field_info.alias else field_name

            input_val = None
            found_key = False

            if alias_key in data:
                input_val = data[alias_key]
                found_key = True
            elif field_name in data:
                input_val = data[field_name]
                found_key = True

            if found_key:
                validated_val = _validate_internal(
                    effective_type,
                    input_val,
                    field_path,
                    errors,
                    merged_map,
                    context,
                    strict,
                    allow_async_validators,
                )

                if field_info is not None:
                    _check_field_constraints(field_info, validated_val, field_path, errors)

                if field_name in custom_validators:
                    for v_func in custom_validators[field_name]:
                        if inspect.iscoroutinefunction(v_func):
                            if not allow_async_validators:
                                errors.append(
                                    FieldError(
                                        path=field_path,
                                        expected="sync validator",
                                        actual_value=validated_val,
                                        message=(
                                            f"Async field validator '{v_func.__name__}'"
                                            f" found on field '{field_name}'. Use"
                                            " async_validate() instead of validate()."
                                        ),
                                    )
                                )
                            continue

                        try:
                            sig = inspect.signature(v_func)
                            params = sig.parameters
                            param_names = list(params.keys())

                            if "context" in param_names:
                                if len(param_names) >= 3 or (
                                    len(param_names) == 2 and param_names[0] != "context"
                                ):
                                    validated_val = v_func(
                                        raw_class, validated_val, context=context
                                    )
                                else:
                                    validated_val = v_func(validated_val, context=context)
                            elif len(param_names) >= 2:
                                validated_val = v_func(raw_class, validated_val)
                            else:
                                validated_val = v_func(validated_val)
                        except (ValueError, TypeError, AssertionError) as err:
                            errors.append(
                                FieldError(
                                    path=field_path,
                                    expected="custom validator check",
                                    actual_value=validated_val,
                                    message=str(err),
                                )
                            )

                kwargs[field_name] = validated_val

            elif field_info is not None and field_info.has_default():
                default_val = field_info.get_default()
                kwargs[field_name] = default_val
            elif hasattr(raw_class, field_name) and not isinstance(
                getattr(raw_class, field_name), FieldInfo
            ):
                kwargs[field_name] = getattr(raw_class, field_name)
            elif is_optional_type(effective_type):
                kwargs[field_name] = None
            else:
                errors.append(
                    FieldError(
                        path=field_path,
                        expected=getattr(effective_type, "__name__", str(effective_type)),
                        actual_value=None,
                        message=f"Missing required field '{field_name}'",
                    )
                )

        instance = raw_class(**kwargs)

        # Run @model_validator(mode="after")
        for mv in model_validators.get("after", []):
            try:
                sig = inspect.signature(mv)
                params_count = len(sig.parameters)
                if params_count >= 2:
                    res_instance = mv(raw_class, instance)
                else:
                    res_instance = mv(instance)
                if res_instance is not None:
                    instance = res_instance
            except (ValueError, TypeError, AssertionError) as err:
                errors.append(
                    FieldError(
                        path=path,
                        expected="model validator after check",
                        actual_value=instance,
                        message=str(err),
                    )
                )

        return instance

    # 12. Basic Primitives & Standard Types
    if isinstance(target_type, type):
        if target_type is int and isinstance(data, bool):
            errors.append(
                FieldError(
                    path=path,
                    expected="int",
                    actual_value=data,
                    message="Expected int, got bool",
                )
            )
            return None
        if target_type is bool and not isinstance(data, bool):
            if not strict and isinstance(data, (int, str)):
                if data in (1, "1", "true", "True", "TRUE"):
                    return True
                if data in (0, "0", "false", "False", "FALSE"):
                    return False

            errors.append(
                FieldError(
                    path=path,
                    expected="bool",
                    actual_value=data,
                    message=f"Expected bool, got {type(data).__name__}",
                )
            )
            return None

        if isinstance(data, target_type):
            return data

        if not strict:
            if target_type is int and isinstance(data, (str, float)):
                try:
                    return int(data)
                except ValueError:
                    pass
            elif target_type is float and isinstance(data, (str, int)):
                try:
                    return float(data)
                except ValueError:
                    pass
            elif target_type is str:
                return str(data)

        errors.append(
            FieldError(
                path=path,
                expected=target_type.__name__,
                actual_value=data,
                message=f"Expected {target_type.__name__}, got {type(data).__name__}",
            )
        )
        return None

    return data
