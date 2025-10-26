import pytest
from typed_schema_validator import Schema, ValidationError, model_validator, validate


class Registration(Schema):
    password: str
    confirm_password: str

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class SanitizedInput(Schema):
    raw_text: str

    @model_validator(mode="before")
    def sanitize(cls, data: dict) -> dict:
        if "raw_text" in data and isinstance(data["raw_text"], str):
            data["raw_text"] = data["raw_text"].strip().lower()
        return data


def test_model_validator_after_success():
    data = {"password": "secret_pass_123", "confirm_password": "secret_pass_123"}
    reg = validate(Registration, data)
    assert reg.password == "secret_pass_123"


def test_model_validator_after_failure():
    data = {"password": "pass1", "confirm_password": "pass2"}
    with pytest.raises(ValidationError) as exc_info:
        validate(Registration, data)
    errs = exc_info.value.errors
    assert any("Passwords do not match" in e.message for e in errs)


def test_model_validator_before():
    data = {"raw_text": "  Hello WORLD  "}
    res = validate(SanitizedInput, data)
    assert res.raw_text == "hello world"
