import enum
import inspect
import types
import typing
from typing import Any, Literal, get_args, get_origin

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


def validate[T](target_type: Any, data: Any, path: str = "") -> T:
    """
    Validate `data` against `target_type` (including PEP 695 generics, aliases, unions, schemas).
    Raises ValidationError if data fails to match target_type or field constraints.
    """
    errors: list[FieldError] = []
    result = _validate_internal(target_type, data, path, errors, type_var_map={})
    if errors:
        raise ValidationError(errors)
    return result


def _check_field_constraints(
    field_info: FieldInfo, val: Any, path: str, errors: list[FieldError]
) -> None:
    """Validate value against FieldInfo constraint parameters."""
    if val is None:
        return

    # Length constraints (str, list, dict, set, tuple)
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

    # Numeric constraints (int, float)
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

    # Pattern constraint (regex on str)
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
) -> Any:
    # 1. Build type var mapping from specialized generic / alias args (e.g., ItemList[Config])
    base_origin, new_type_var_map = build_type_var_map(target_type)
    merged_map = {**type_var_map, **new_type_var_map}

    # 2. Resolve PEP 695 TypeAliasType (e.g., `type Result[T] = dict[str, T]`)
    if is_pep695_alias(target_type):
        target_type = target_type.__value__
    elif is_pep695_alias(base_origin):
        target_type = base_origin.__value__

    # 3. Substitute any active TypeVars from generic parent context
    target_type = substitute_typevars(target_type, merged_map)

    # 4. Any / object type bypass
    if target_type is Any or target_type is object:
        return data

    # Re-evaluate base_origin & new_type_var_map after substitution/unwrapping if needed
    base_origin, extra_type_var_map = build_type_var_map(target_type)
    merged_map.update(extra_type_var_map)

    # 5. Union Types (e.g. int | str, T | None)
    if is_union_type(target_type):
        union_args = get_union_args(target_type)
        if data is None and type(None) in union_args:
            return None

        for variant in union_args:
            if variant is type(None) and data is not None:
                continue
            sub_errors: list[FieldError] = []
            res = _validate_internal(variant, data, path, sub_errors, merged_map)
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

    # 8. Container Origin Types (list, dict, set, tuple)
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
                    item_type, item, item_path, errors, merged_map
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
                vk = _validate_internal(key_type, k, key_path, errors, merged_map)
                vv = _validate_internal(val_type, v, val_path, errors, merged_map)
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
                    _validate_internal(item_type, item, item_path, errors, merged_map)
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
                        )
                        for i, item in enumerate(data)
                    )
                    return validated_tuple

    # 9. Schema Subclass Validation
    raw_class = base_origin if inspect.isclass(base_origin) else target_type
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

        annotations = raw_class._get_resolved_annotations()
        custom_validators = raw_class._get_field_validators()
        kwargs = {}

        for field_name, field_type in annotations.items():
            field_path = f"{path}.{field_name}" if path else field_name
            effective_type = substitute_typevars(field_type, merged_map)
            field_info: FieldInfo | None = None

            if hasattr(raw_class, field_name):
                class_attr = getattr(raw_class, field_name)
                if isinstance(class_attr, FieldInfo):
                    field_info = class_attr

            if field_name in data:
                val = data[field_name]
                validated_val = _validate_internal(
                    effective_type, val, field_path, errors, merged_map
                )

                # Check FieldInfo constraints if present
                if field_info is not None:
                    _check_field_constraints(field_info, validated_val, field_path, errors)

                # Run custom @field_validator functions
                if field_name in custom_validators:
                    for v_func in custom_validators[field_name]:
                        try:
                            # Invoke validator function (as classmethod or function)
                            sig = inspect.signature(v_func)
                            params_count = len(sig.parameters)
                            if params_count >= 2:
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
        return instance

    # 10. Basic Primitives & Standard Types
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
