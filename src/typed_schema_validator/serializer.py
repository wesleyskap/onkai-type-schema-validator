import dataclasses
import enum
from datetime import date, datetime
from typing import Any
from typed_schema_validator.field import FieldInfo
from typed_schema_validator.schema import Schema


def dump(obj: Any, by_alias: bool = False) -> Any:
    """
    Recursively serialize schema instances, dataclasses, enums, dates/datetimes,
    and standard collections to standard JSON-compatible Python primitives.
    
    If `by_alias=True`, schema fields with an alias will be dumped using their alias name.
    """
    if obj is None:
        return None

    if isinstance(obj, Schema):
        hints = obj._get_resolved_annotations()
        result = {}
        for key in hints:
            val = getattr(obj, key, None)
            dump_key = key
            if by_alias and hasattr(obj.__class__, key):
                attr_val = getattr(obj.__class__, key)
                if isinstance(attr_val, FieldInfo) and attr_val.alias:
                    dump_key = attr_val.alias
            result[dump_key] = dump(val, by_alias=by_alias)
        return result

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        result = {}
        for field_obj in dataclasses.fields(obj):
            key = field_obj.name
            val = getattr(obj, key, None)
            result[key] = dump(val, by_alias=by_alias)
        return result

    if isinstance(obj, enum.Enum):
        return obj.value

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if isinstance(obj, dict):
        return {str(k): dump(v, by_alias=by_alias) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [dump(item, by_alias=by_alias) for item in obj]

    return obj
