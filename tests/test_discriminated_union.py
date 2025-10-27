from typing import Literal
import pytest
from typed_schema_validator import Schema, ValidationError, validate


class Cat(Schema):
    pet_type: Literal["cat"]
    meow_volume: int


class Dog(Schema):
    pet_type: Literal["dog"]
    bark_pitch: str


type Pet = Cat | Dog


def test_discriminated_union_cat():
    data = {"pet_type": "cat", "meow_volume": 85}
    pet = validate(Pet, data)
    assert isinstance(pet, Cat)
    assert pet.pet_type == "cat"
    assert pet.meow_volume == 85


def test_discriminated_union_dog():
    data = {"pet_type": "dog", "bark_pitch": "high"}
    pet = validate(Pet, data)
    assert isinstance(pet, Dog)
    assert pet.pet_type == "dog"
    assert pet.bark_pitch == "high"


def test_discriminated_union_invalid_payload():
    data = {"pet_type": "cat", "meow_volume": "not_an_int"}
    with pytest.raises(ValidationError) as exc_info:
        validate(Pet, data)
    errs = exc_info.value.errors
    assert any("meow_volume" in e.path for e in errs)
