import pytest
from typed_schema_validator import Schema, ValidationError, field_validator, validate


class UserRegistration(Schema):
    email: str
    confirm_email: str

    @field_validator("email")
    def validate_email_domain(cls, v: str) -> str:
        if "@company.com" not in v.lower():
            raise ValueError("Email must belong to @company.com domain")
        return v.lower()


def test_custom_validator_success():
    data = {
        "email": "ALICE@COMPANY.COM",
        "confirm_email": "alice@company.com"
    }
    user = validate(UserRegistration, data)
    assert user.email == "alice@company.com"


def test_custom_validator_failure():
    data = {
        "email": "bob@gmail.com",
        "confirm_email": "bob@gmail.com"
    }
    with pytest.raises(ValidationError) as exc_info:
        validate(UserRegistration, data)
    errs = exc_info.value.errors
    assert any(e.path == "email" and "@company.com" in e.message for e in errs)
