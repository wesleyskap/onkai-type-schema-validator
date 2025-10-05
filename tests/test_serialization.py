from datetime import date
import enum
from typed_schema_validator import Schema, dump, validate


class Role(enum.Enum):
    ADMIN = "admin"
    USER = "user"


class Member[T](Schema):
    name: str
    role: Role
    joined: date
    extra: T


def test_serialization():
    m = Member[dict](
        name="Carlos",
        role=Role.ADMIN,
        joined=date(2025, 1, 15),
        extra={"active": True}
    )
    
    serialized = dump(m)
    assert serialized == {
        "name": "Carlos",
        "role": "admin",
        "joined": "2025-01-15",
        "extra": {"active": True}
    }


def test_schema_instance_dump_method():
    class Simple(Schema):
        a: int
        b: str = "default"

    obj = validate(Simple, {"a": 10})
    assert obj.dump() == {"a": 10, "b": "default"}
