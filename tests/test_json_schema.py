from dataclasses import dataclass
import enum
from typed_schema_validator import Field, Schema, to_json_schema


class UserStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class UserProfile(Schema):
    username: str = Field(min_length=3, max_length=20, pattern=r"^\w+$")
    age: int = Field(gt=0, le=120, description="Age of the user")
    status: UserStatus = UserStatus.ACTIVE
    bio: str | None = None


class Response[T](Schema):
    code: int
    payload: T


@dataclass
class Location:
    latitude: float
    longitude: float


def test_schema_model_json_schema():
    schema = UserProfile.json_schema()
    assert schema["type"] == "object"
    assert "username" in schema["properties"]
    assert schema["properties"]["username"]["minLength"] == 3
    assert schema["properties"]["username"]["maxLength"] == 20
    assert schema["properties"]["username"]["pattern"] == r"^\w+$"
    assert schema["properties"]["age"]["exclusiveMinimum"] == 0
    assert schema["properties"]["age"]["description"] == "Age of the user"
    assert schema["properties"]["bio"]["nullable"] is True
    assert "username" in schema["required"]
    assert "age" in schema["required"]


def test_pep695_generic_json_schema():
    schema = to_json_schema(Response[Location])
    assert schema["type"] == "object"
    assert schema["properties"]["code"]["type"] == "integer"
    assert schema["properties"]["payload"]["type"] == "object"
    assert schema["properties"]["payload"]["properties"]["latitude"]["type"] == "number"
    assert schema["properties"]["payload"]["properties"]["longitude"]["type"] == "number"


def test_enum_and_primitive_json_schema():
    assert to_json_schema(int) == {"type": "integer"}
    assert to_json_schema(str) == {"type": "string"}
    assert to_json_schema(UserStatus) == {"type": "string", "enum": ["active", "inactive"]}
