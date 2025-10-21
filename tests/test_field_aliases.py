import pytest
from typed_schema_validator import Field, Schema, dump, validate


class UserProfile(Schema):
    user_id: int = Field(alias="userId")
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    email: str


class StrictAliased(Schema, extra="forbid"):
    user_id: int = Field(alias="userId")


def test_validation_by_alias():
    data = {
        "userId": 100,
        "firstName": "John",
        "lastName": "Doe",
        "email": "john@example.com",
    }
    user = validate(UserProfile, data)
    assert user.user_id == 100
    assert user.first_name == "John"
    assert user.last_name == "Doe"
    assert user.email == "john@example.com"


def test_dump_by_alias():
    user = UserProfile(
        user_id=200,
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com",
    )

    # Standard dump (python attribute names)
    standard_dict = dump(user)
    assert standard_dict == {
        "user_id": 200,
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@example.com",
    }

    # Dump by alias
    aliased_dict = dump(user, by_alias=True)
    assert aliased_dict == {
        "userId": 200,
        "firstName": "Jane",
        "lastName": "Smith",
        "email": "jane@example.com",
    }


def test_strict_aliased_extra_forbid():
    data = {"userId": 100}
    obj = validate(StrictAliased, data)
    assert obj.user_id == 100
