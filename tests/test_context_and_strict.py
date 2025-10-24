import pytest
from typed_schema_validator import Schema, ValidationError, field_validator, validate


class RolePermission(Schema):
    role: str

    @field_validator("role")
    def validate_admin(cls, v: str, context: dict) -> str:
        if v == "admin" and context.get("user") != "root":
            raise ValueError("Only root can assign admin role")
        return v


class CoercedTypes(Schema):
    age: int
    score: float
    active: bool


def test_context_validation_success():
    res = validate(RolePermission, {"role": "admin"}, context={"user": "root"})
    assert res.role == "admin"


def test_context_validation_failure():
    with pytest.raises(ValidationError) as exc_info:
        validate(RolePermission, {"role": "admin"}, context={"user": "guest"})
    errs = exc_info.value.errors
    assert any("Only root can assign admin role" in e.message for e in errs)


def test_non_strict_coercion():
    data = {"age": "25", "score": "98.5", "active": "true"}
    res = validate(CoercedTypes, data, strict=False)
    assert res.age == 25
    assert res.score == 98.5
    assert res.active is True


def test_strict_mode_fails_on_string_coercion():
    data = {"age": "25", "score": "98.5", "active": True}
    with pytest.raises(ValidationError) as exc_info:
        validate(CoercedTypes, data, strict=True)
    errs = exc_info.value.errors
    assert len(errs) == 2  # age and score fail strict type check
