# Typed Schema Validator

Typed Schema Validator is a data validation and serialization framework for Python 3.12+ applications using the native type parameter syntax (PEP 695).

## Features

- **PEP 695 Generic Syntax**: Native support for `class Model[T]: ...` and `type Alias[T] = ...` without `TypeVar` or `Generic` boilerplate.
- **Zero Dependencies**: Lightweight implementation relying exclusively on Python 3.12+ standard library features.
- **Field Constraints**: Declarative validation using `Field(min_length=..., max_length=..., gt=..., lt=..., pattern=...)`.
- **Custom Field Validators**: Flexible `@field_validator` decorator for custom validation logic and value transformation.
- **Strict Runtime Validation**: Recursive validation for primitive scalars, generic models, unions (`T | None`, `int | str`), enums, literals, lists, dicts, sets, and tuples.
- **Recursive Serialization**: Built-in `dump()` method to convert schema instances and nested structures into JSON-compatible Python primitives.
- **Detailed Error Reporting**: `ValidationError` with field-level path tracking (`FieldError`), expected types, and actual values.
- **Class Default Values**: Automatic fallback to class-level default values, default factories, and optional field resolution.

## Requirements

- Python >= 3.12

## Installation

```bash
pip install typed-schema-validator
```

## Quick Start

### Basic Schema Validation

```python
from typed_schema_validator import Schema, validate, dump

class User(Schema):
    id: int
    name: str
    email: str | None = None

raw_data = {
    "id": 1,
    "name": "Alice"
}

user = validate(User, raw_data)
print(user.name)  # Alice
print(user.email) # None

# Dump to dictionary
data_dict = user.dump()
```

### Field Constraints and Custom Validators

```python
from typed_schema_validator import Schema, Field, field_validator, validate

class UserRegistration(Schema):
    username: str = Field(min_length=3, max_length=15, pattern=r"^[a-zA-Z0-9_]+$")
    age: int = Field(gt=0, le=120)
    email: str

    @field_validator("email")
    def validate_email_domain(cls, v: str) -> str:
        if "@company.com" not in v:
            raise ValueError("Email must belong to @company.com domain")
        return v.lower()

payload = {
    "username": "user_123",
    "age": 28,
    "email": "ALICE@COMPANY.COM"
}

user = validate(UserRegistration, payload)
print(user.email) # alice@company.com
```

### PEP 695 Generics Validation

```python
from typed_schema_validator import Schema, validate, dump

class Response[T](Schema):
    status_code: int
    data: T
    tags: list[str] = []

class Product(Schema):
    sku: str
    price: float

payload = {
    "status_code": 200,
    "data": {
        "sku": "PROD-100",
        "price": 49.99
    },
    "tags": ["electronics", "sale"]
}

response = validate(Response[Product], payload)
print(response.data.sku)    # PROD-100
print(response.data.price)  # 49.99
```

### PEP 695 Type Aliases Validation

```python
from typed_schema_validator import Schema, validate

type ResultMap[T] = dict[str, T | None]

data = {
    "primary": 100,
    "secondary": None
}

result = validate(ResultMap[int], data)
print(result)  # {'primary': 100, 'secondary': None}
```

### Handling Validation Errors

```python
from typed_schema_validator import Schema, validate, ValidationError

class Account(Schema):
    username: str
    balance: float

try:
    validate(Account, {"username": "admin", "balance": "invalid_number"})
except ValidationError as e:
    for err in e.errors:
        print(f"Path: {err.path}, Expected: {err.expected}, Actual: {err.actual_value}")
```

## Architecture

1. **Schema Base (`src/typed_schema_validator/schema.py`)**: Defines class attribute resolution, field annotations, equality checking, and custom validator collection.
2. **Field & Constraints (`src/typed_schema_validator/field.py`)**: Contains `FieldInfo` container for declarative validation rules (min/max length, numeric bounds, regex patterns, default factories).
3. **Custom Validators (`src/typed_schema_validator/field_validator.py`)**: Implements `@field_validator` decorator to register custom validation and transformation methods.
4. **Type Inspector (`src/typed_schema_validator/type_inspector.py`)**: Handles runtime inspection of PEP 695 type parameters (`__type_params__`), generic specialization, and type variable substitutions.
5. **Validator Engine (`src/typed_schema_validator/validator.py`)**: Core recursive validation engine processing unions, aliases, containers, enums, literals, field constraints, custom validators, and schema instances.
6. **Serializer Engine (`src/typed_schema_validator/serializer.py`)**: Converts schema models, datetimes, enums, and collections back to standard Python dictionaries and primitives.
7. **Errors (`src/typed_schema_validator/errors.py`)**: Defines `FieldError` for detailed path location tracking and `ValidationError` exceptions.

## Running Tests

```bash
python -m pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
