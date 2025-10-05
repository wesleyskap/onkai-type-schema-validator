import pytest
from typed_schema_validator import Schema, ValidationError, validate


class Profile(Schema):
    age: int
    bio: str | None = None


class UserAccount(Schema):
    username: str
    profile: Profile
    roles: list[str]


def test_missing_required_field():
    with pytest.raises(ValidationError) as exc_info:
        validate(UserAccount, {"username": "admin", "roles": ["super"]})
    
    errs = exc_info.value.errors
    assert len(errs) == 1
    assert errs[0].path == "profile"
    assert "Missing required field" in errs[0].message


def test_invalid_type_nested():
    payload = {
        "username": "admin",
        "profile": {
            "age": "invalid_int_string"
        },
        "roles": ["super"]
    }
    
    with pytest.raises(ValidationError) as exc_info:
        validate(UserAccount, payload)
    
    errs = exc_info.value.errors
    assert any(e.path == "profile.age" for e in errs)


def test_invalid_list_element():
    payload = {
        "username": "admin",
        "profile": {
            "age": 25
        },
        "roles": ["super", 123]
    }
    
    with pytest.raises(ValidationError) as exc_info:
        validate(UserAccount, payload)
    
    errs = exc_info.value.errors
    assert any(e.path == "roles[1]" for e in errs)
