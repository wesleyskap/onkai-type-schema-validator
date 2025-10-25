import asyncio
import pytest
from typed_schema_validator import Schema, ValidationError, async_validate, field_validator, validate


class AsyncUser(Schema):
    username: str
    email: str

    @field_validator("email")
    async def check_email_available(cls, v: str) -> str:
        await asyncio.sleep(0.001)  # Simulate async DB lookup
        if v == "taken@example.com":
            raise ValueError("Email already in use")
        return v.lower()


def test_async_validation_success():
    async def _test():
        data = {"username": "alice", "email": "ALICE@EXAMPLE.COM"}
        user = await async_validate(AsyncUser, data)
        assert user.username == "alice"
        assert user.email == "alice@example.com"

    asyncio.run(_test())


def test_async_validation_failure():
    async def _test():
        data = {"username": "bob", "email": "taken@example.com"}
        with pytest.raises(ValidationError) as exc_info:
            await async_validate(AsyncUser, data)
        errs = exc_info.value.errors
        assert any("Email already in use" in e.message for e in errs)

    asyncio.run(_test())


def test_sync_validation_fails_on_async_validator():
    data = {"username": "alice", "email": "alice@example.com"}
    with pytest.raises(ValidationError) as exc_info:
        validate(AsyncUser, data)
    errs = exc_info.value.errors
    assert any("Async field validator" in e.message for e in errs)
