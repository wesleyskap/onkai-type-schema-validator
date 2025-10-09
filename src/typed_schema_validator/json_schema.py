import dataclasses
import enum
import inspect
import types
import typing
from typing import Any, Literal, get_args, get_origin, get_type_hints, is_typeddict

from typed_schema_validator.field import FieldInfo
from typed_schema_validator.schema import Schema
from typed_schema_validator.type_inspector import (
    build_type_var_map,
    get_union_args,
    is_pep695_alias,
    is_union_type,
    substitute_typevars,
)


def to_json_schema(target_type: Any) -> dict[str, Any]:
    """
    Generate a JSON Schema (Draft-07 / OpenAPI compatible) dictionary
    for a given type, PEP 695 generic, Schema, dataclass, or TypedDict.
    """
    return _generate_schema_internal(target_type, type_var_map={})


def _generate_schema_internal(
    target_type: Any, type_var_map: dict[Any, Any]
) -> dict[str, Any]:
    base_origin, new_type_var_map = build_type_var_map(target_type)
    merged_map = {**type_var_map, **new_type_var_map}

    if is_pep695_alias(target_type):
        target_type = target_type.__value__
    elif is_pep695_alias(base_origin):
        target_type = base_origin.__value__

    target_type = substitute_typevars(target_type, merged_map)

    if target_type is Any or target_type is object:
        return {}

    base_origin, extra_type_var_map = build_type_var_map(target_type)
    merged_map.update(extra_type_var_map)

    # 1. Union types
    if is_union_type(target_type):
        args = get_union_args(target_type)
        non_null_args = [a for a in args if a is not type(None)]
        has_null = type(None) in args

        if len(non_null_args) == 1:
            schema = _generate_schema_internal(non_null_args[0], merged_map)
            if has_null:
                schema["nullable"] = True
            return schema

        schemas = [_generate_schema_internal(a, merged_map) for a in non_null_args]
        result: dict[str, Any] = {"anyOf": schemas}
        if has_null:
            result["nullable"] = True
        return result

    # 2. Literal types
    if get_origin(target_type) is Literal:
        allowed = list(get_args(target_type))
        return {"enum": allowed}

    # 3. Enum types
    if isinstance(target_type, type) and issubclass(target_type, enum.Enum):
        values = [e.value for e in target_type]
        enum_type = "string" if all(isinstance(v, str) for v in values) else "integer"
        return {"type": enum_type, "enum": values}

    # 4. Primitives
    if target_type is int:
        return {"type": "integer"}
    if target_type is float:
        return {"type": "number"}
    if target_type is str:
        return {"type": "string"}
    if target_type is bool:
        return {"type": "boolean"}

    raw_class = base_origin if inspect.isclass(base_origin) else target_type

    # 5. Schema subclass
    if inspect.isclass(raw_class) and issubclass(raw_class, Schema):
        annotations = raw_class._get_resolved_annotations()
        properties: dict[str, Any] = {}
        required: list[str] = []

        for field_name, field_type in annotations.items():
            effective_type = substitute_typevars(field_type, merged_map)
            field_schema = _generate_schema_internal(effective_type, merged_map)
            field_info: FieldInfo | None = None

            if hasattr(raw_class, field_name):
                class_attr = getattr(raw_class, field_name)
                if isinstance(class_attr, FieldInfo):
                    field_info = class_attr

            if field_info is not None:
                if field_info.min_length is not None:
                    field_schema["minLength"] = field_info.min_length
                if field_info.max_length is not None:
                    field_schema["maxLength"] = field_info.max_length
                if field_info.gt is not None:
                    field_schema["exclusiveMinimum"] = field_info.gt
                if field_info.ge is not None:
                    field_schema["minimum"] = field_info.ge
                if field_info.lt is not None:
                    field_schema["exclusiveMaximum"] = field_info.lt
                if field_info.le is not None:
                    field_schema["maximum"] = field_info.le
                if field_info.pattern is not None:
                    field_schema["pattern"] = field_info.pattern.pattern
                if field_info.description is not None:
                    field_schema["description"] = field_info.description
                if field_info.has_default():
                    default_val = field_info.get_default()
                    if default_val is not None:
                        field_schema["default"] = default_val

            properties[field_name] = field_schema

            # Check if required
            has_def = (
                (field_info is not None and field_info.has_default())
                or (
                    hasattr(raw_class, field_name)
                    and not isinstance(getattr(raw_class, field_name), FieldInfo)
                )
                or field_schema.get("nullable") is True
            )
            if not has_def:
                required.append(field_name)

        schema_res: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema_res["required"] = required
        return schema_res

    # 6. Dataclass
    if inspect.isclass(raw_class) and dataclasses.is_dataclass(raw_class):
        dc_fields = dataclasses.fields(raw_class)
        properties = {}
        required = []

        for f_obj in dc_fields:
            effective_type = substitute_typevars(f_obj.type, merged_map)
            field_schema = _generate_schema_internal(effective_type, merged_map)
            properties[f_obj.name] = field_schema

            has_def = (
                f_obj.default is not dataclasses.MISSING
                or f_obj.default_factory is not dataclasses.MISSING
                or field_schema.get("nullable") is True
            )
            if not has_def:
                required.append(f_obj.name)

        schema_res = {"type": "object", "properties": properties}
        if required:
            schema_res["required"] = required
        return schema_res

    # 7. TypedDict
    if inspect.isclass(raw_class) and is_typeddict(raw_class):
        annotations = get_type_hints(raw_class, include_extras=True)
        required_keys = getattr(raw_class, "__required_keys__", set(annotations.keys()))
        properties = {}
        required = []

        for key, raw_field_type in annotations.items():
            effective_type = substitute_typevars(raw_field_type, merged_map)
            field_origin = get_origin(effective_type)
            is_req = key in required_keys

            if field_origin is typing.Required:
                effective_type = get_args(effective_type)[0]
                is_req = True
            elif field_origin is typing.NotRequired:
                effective_type = get_args(effective_type)[0]
                is_req = False

            field_schema = _generate_schema_internal(effective_type, merged_map)
            properties[key] = field_schema
            if is_req:
                required.append(key)

        schema_res = {"type": "object", "properties": properties}
        if required:
            schema_res["required"] = required
        return schema_res

    # 8. Container origin types (list, dict, set, tuple)
    origin = base_origin if base_origin is not target_type else get_origin(target_type)
    if origin is not None:
        args = get_args(target_type)

        if origin is list or origin is typing.List or origin is set or origin is typing.Set:
            item_type = args[0] if args else Any
            return {
                "type": "array",
                "items": _generate_schema_internal(item_type, merged_map),
            }

        if origin is dict or origin is typing.Dict:
            val_type = args[1] if len(args) > 1 else Any
            return {
                "type": "object",
                "additionalProperties": _generate_schema_internal(val_type, merged_map),
            }

        if origin is tuple or origin is typing.Tuple:
            if args:
                if len(args) == 2 and args[1] is ...:
                    return {
                        "type": "array",
                        "items": _generate_schema_internal(args[0], merged_map),
                    }
                items_schemas = [
                    _generate_schema_internal(arg, merged_map) for arg in args
                ]
                return {
                    "type": "array",
                    "prefixItems": items_schemas,
                    "minItems": len(args),
                    "maxItems": len(args),
                }

    return {}
