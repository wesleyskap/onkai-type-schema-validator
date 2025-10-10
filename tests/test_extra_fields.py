import pytest
from typed_schema_validator import Schema, ValidationError, validate


class DefaultUser(Schema):
    id: int
    name: str


class StrictUser(Schema, extra="forbid"):
    id: int
    name: str


def test_extra_fields_ignored_by_default():
    data = {"id": 1, "name": "Alice", "unexpected_field": "bar"}
    user = validate(DefaultUser, data)
    assert user.id == 1
    assert user.name == "Alice"
    assert not hasattr(user, "unexpected_field")


def test_extra_fields_forbidden():
    data = {"id": 1, "name": "Alice", "unknown_key": "bar"}
    with pytest.raises(ValidationError) as exc_info:
        validate(StrictUser, data)

    errs = exc_info.value.errors
    assert len(errs) == 1
    assert errs[0].path == "unknown_key"
    assert "Unexpected extra field" in errs[0].message
