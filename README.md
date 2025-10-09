# Typed Schema Validator

Typed Schema Validator is a data validation and serialization framework for Python 3.12+ applications using the native type parameter syntax (PEP 695).

## Features

- **PEP 695 Generic Syntax**: Native support for `class Model[T]: ...` and `type Alias[T] = ...` without `TypeVar` or `Generic` boilerplate.
- **Dataclass & TypedDict Support**: Direct validation and serialization for standard Python `@dataclass` and `TypedDict` structures.
- **JSON Schema / OpenAPI Generation**: Automatic generation of JSON Schema (Draft-07) dictionaries via `to_json_schema()` or `Schema.json_schema()`.
- **Zero Dependencies**: Lightweight implementation relying exclusively on Python 3.12+ standard library features.
- **Field Constraints**: Declarative validation using `Field(min_length=..., max_length=..., gt=..., lt=..., pattern=...)`.
- **Custom Field Validators**: Flexible `@field_validator` decorator for custom validation logic and value transformation.
- **Strict Runtime Validation**: Recursive validation for primitive scalars, generic models, unions (`T | None`, `int | str`), enums, literals, lists, dicts, sets, and tuples.
- **Recursive Serialization**: Built-in `dump()` method to convert schema instances, dataclasses, and nested structures into JSON-compatible Python primitives.
- **Detailed Error Reporting**: `ValidationError` with field-level path tracking (`FieldError`), expected types, and actual values.

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

### JSON Schema / OpenAPI Generation

```python
from typed_schema_validator import Schema, Field, to_json_schema

class Product[T](Schema):
    sku: str = Field(min_length=3, pattern=r"^[A-Z0-9-]+$")
    price: float = Field(gt=0)
    details: T

# Generate JSON Schema for specialized PEP 695 generic model
schema_dict = to_json_schema(Product[dict[str, str]])
print(schema_dict)
```

### Dataclass and TypedDict Validation

```python
from dataclasses import dataclass
from typing import TypedDict
from typed_schema_validator import validate, dump

@dataclass
class Point[T]:
    x: T
    y: T

class UserPayload(TypedDict):
    username: str
    age: int

# Validating dataclass instance
point = validate(Point[float], {"x": 10.5, "y": 20.0})
print(point.x) # 10.5

# Validating TypedDict
payload = validate(UserPayload, {"username": "carlos", "age": 30})
print(payload["username"]) # carlos

# Dumping dataclass
print(dump(point)) # {'x': 10.5, 'y': 20.0}
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
        if "@company.com" not in v.lower():
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

1. **Schema Base (`src/typed_schema_validator/schema.py`)**: Defines class attribute resolution, field annotations, equality checking, custom validator collection, and JSON Schema export.
2. **JSON Schema Engine (`src/typed_schema_validator/json_schema.py`)**: Generates OpenAPI / JSON Schema Draft-07 dictionaries resolving PEP 695 generic type parameters and constraints.
3. **Field & Constraints (`src/typed_schema_validator/field.py`)**: Contains `FieldInfo` container for declarative validation rules (min/max length, numeric bounds, regex patterns, default factories).
4. **Custom Validators (`src/typed_schema_validator/field_validator.py`)**: Implements `@field_validator` decorator to register custom validation and transformation methods.
5. **Type Inspector (`src/typed_schema_validator/type_inspector.py`)**: Handles runtime inspection of PEP 695 type parameters (`__type_params__`), generic specialization, and type variable substitutions.
6. **Validator Engine (`src/typed_schema_validator/validator.py`)**: Core recursive validation engine processing dataclasses, typeddicts, unions, aliases, containers, enums, literals, field constraints, custom validators, and schema instances.
7. **Serializer Engine (`src/typed_schema_validator/serializer.py`)**: Converts schema models, dataclasses, datetimes, enums, and collections back to standard Python dictionaries and primitives.
8. **Errors (`src/typed_schema_validator/errors.py`)**: Defines `FieldError` for detailed path location tracking and `ValidationError` exceptions.

## Running Tests

```bash
python -m pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
