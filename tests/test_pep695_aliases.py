import pytest
from typed_schema_validator import Schema, validate

# PEP 695 type aliases syntax (Python 3.12+)
type ResultDict[T] = dict[str, T | None]
type ItemList[T] = list[T]


class Config(Schema):
    enabled: bool
    version: int


def test_type_alias_dict():
    data = {"key1": 100, "key2": None}
    res = validate(ResultDict[int], data)
    assert res == {"key1": 100, "key2": None}


def test_type_alias_list_schema():
    data = [{"enabled": True, "version": 1}, {"enabled": False, "version": 2}]
    res = validate(ItemList[Config], data)
    assert len(res) == 2
    assert isinstance(res[0], Config)
    assert res[0].enabled is True
    assert res[1].version == 2
