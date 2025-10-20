import pytest
from typed_schema_validator import Schema, validate


class FrozenUser(Schema, frozen=True):
    id: int
    name: str


class MutableUser(Schema):
    id: int
    name: str


def test_frozen_schema_mutation_fails():
    user = validate(FrozenUser, {"id": 1, "name": "Alice"})
    assert user.id == 1
    assert user.name == "Alice"

    with pytest.raises(TypeError) as exc_info:
        user.name = "Bob"
    assert "Cannot mutate field 'name'" in str(exc_info.value)


def test_frozen_schema_deletion_fails():
    user = validate(FrozenUser, {"id": 1, "name": "Alice"})

    with pytest.raises(TypeError) as exc_info:
        del user.name
    assert "Cannot delete field 'name'" in str(exc_info.value)


def test_frozen_schema_hashability():
    u1 = validate(FrozenUser, {"id": 1, "name": "Alice"})
    u2 = validate(FrozenUser, {"id": 1, "name": "Alice"})
    u3 = validate(FrozenUser, {"id": 2, "name": "Bob"})

    user_set = {u1, u2, u3}
    assert len(user_set) == 2
    assert u1 in user_set
    assert hash(u1) == hash(u2)


def test_mutable_schema_unhashable():
    user = validate(MutableUser, {"id": 1, "name": "Alice"})
    with pytest.raises(TypeError) as exc_info:
        hash(user)
    assert "Unhashable type" in str(exc_info.value)
