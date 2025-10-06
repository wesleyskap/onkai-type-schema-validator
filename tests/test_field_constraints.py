import pytest
from typed_schema_validator import Field, Schema, ValidationError, validate


class AccountProfile(Schema):
    username: str = Field(min_length=3, max_length=15, pattern=r"^[a-zA-Z0-9_]+$")
    age: int = Field(gt=0, le=120)
    score: float = Field(ge=0.0, lt=100.0)
    tags: list[str] = Field(default_factory=list, max_length=3)


def test_valid_account_profile():
    data = {
        "username": "user_123",
        "age": 30,
        "score": 95.5
    }
    profile = validate(AccountProfile, data)
    assert profile.username == "user_123"
    assert profile.age == 30
    assert profile.tags == []


def test_string_length_constraint_failure():
    data = {
        "username": "ab",  # min_length=3
        "age": 30,
        "score": 50.0
    }
    with pytest.raises(ValidationError) as exc_info:
        validate(AccountProfile, data)
    errs = exc_info.value.errors
    assert any(e.path == "username" and "min_length" in e.expected for e in errs)


def test_regex_pattern_failure():
    data = {
        "username": "invalid space!",
        "age": 30,
        "score": 50.0
    }
    with pytest.raises(ValidationError) as exc_info:
        validate(AccountProfile, data)
    errs = exc_info.value.errors
    assert any(e.path == "username" and "pattern" in e.expected for e in errs)


def test_numeric_bounds_failure():
    data = {
        "username": "valid_user",
        "age": 0,  # gt=0 required
        "score": 105.0  # lt=100.0 required
    }
    with pytest.raises(ValidationError) as exc_info:
        validate(AccountProfile, data)
    errs = exc_info.value.errors
    assert len(errs) == 2
