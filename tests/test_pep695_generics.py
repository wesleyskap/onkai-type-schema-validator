import pytest
from typed_schema_validator import Schema, validate


class Container[T](Schema):
    item: T
    tags: list[str] = []


class User(Schema):
    id: int
    name: str


class Response[T](Schema):
    code: int
    data: T
    meta: dict[str, str] = {}


def test_simple_generic_container():
    res = validate(Container[int], {"item": 42, "tags": ["a", "b"]})
    assert res.item == 42
    assert res.tags == ["a", "b"]
    assert isinstance(res, Container)


def test_nested_generic_model():
    payload = {
        "code": 200,
        "data": {
            "id": 10,
            "name": "Alice"
        },
        "meta": {"env": "prod"}
    }
    
    res = validate(Response[User], payload)
    assert res.code == 200
    assert isinstance(res.data, User)
    assert res.data.id == 10
    assert res.data.name == "Alice"
    assert res.meta == {"env": "prod"}


def test_double_nested_generics():
    payload = {
        "item": {
            "code": 201,
            "data": {
                "id": 99,
                "name": "Bob"
            }
        }
    }
    
    res = validate(Container[Response[User]], payload)
    assert isinstance(res.item, Response)
    assert isinstance(res.item.data, User)
    assert res.item.data.id == 99
    assert res.item.data.name == "Bob"
