from dataclasses import dataclass
from typing import NotRequired, Required, TypedDict
import pytest
from typed_schema_validator import dump, validate, ValidationError


# Dataclass test definitions
@dataclass
class Point:
    x: float
    y: float
    label: str = "origin"


@dataclass
class GenericBox[T]:
    content: T
    code: int = 0


# TypedDict test definitions
class UserDict(TypedDict):
    name: str
    age: int


class AdvancedConfig(TypedDict, total=False):
    debug: bool
    retries: Required[int]
    name: NotRequired[str]


def test_dataclass_validation():
    data = {"x": 10.5, "y": 20.0}
    pt = validate(Point, data)
    assert isinstance(pt, Point)
    assert pt.x == 10.5
    assert pt.y == 20.0
    assert pt.label == "origin"


def test_generic_dataclass_validation():
    data = {"content": {"x": 1.0, "y": 2.0}, "code": 200}
    box = validate(GenericBox[Point], data)
    assert isinstance(box, GenericBox)
    assert isinstance(box.content, Point)
    assert box.content.x == 1.0
    assert box.code == 200


def test_dataclass_dump():
    pt = Point(x=3.0, y=4.0, label="target")
    serialized = dump(pt)
    assert serialized == {"x": 3.0, "y": 4.0, "label": "target"}


def test_typeddict_validation():
    data = {"name": "Alice", "age": 25}
    res = validate(UserDict, data)
    assert res == {"name": "Alice", "age": 25}


def test_typeddict_missing_required_key():
    data = {"name": "Alice"}
    with pytest.raises(ValidationError) as exc_info:
        validate(UserDict, data)
    errs = exc_info.value.errors
    assert any(e.path == "age" and "Missing required" in e.message for e in errs)


def test_typeddict_not_required_keys():
    data = {"retries": 3}
    res = validate(AdvancedConfig, data)
    assert res == {"retries": 3}
