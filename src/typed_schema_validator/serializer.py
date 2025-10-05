import enum
from datetime import date, datetime
from typing import Any
from typed_schema_validator.schema import Schema


def dump(obj: Any) -> Any:
    """
    Recursively serialize schema instances, dataclasses, enums, dates/datetimes,
    and standard collections to standard JSON-compatible Python primitives.
    """
    if obj is None:
        return None

    if isinstance(obj, Schema):
        hints = obj._get_resolved_annotations()
        result = {}
        for key in hints:
            val = getattr(obj, key, None)
            result[key] = dump(val)
        return result

    if isinstance(obj, enum.Enum):
        return obj.value

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if isinstance(obj, dict):
        return {str(k): dump(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [dump(item) for item in obj]

    return obj
