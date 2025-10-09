from pathlib import Path
import sys
import time

# Ensure src is in sys.path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from dataclasses import dataclass
from typing import TypedDict
from typed_schema_validator import Field, Schema, dump, to_json_schema, validate


# Benchmarking models
class User(Schema):
    id: int
    username: str = Field(min_length=3, max_length=20)
    email: str | None = None


class Response[T](Schema):
    code: int
    payload: T
    tags: list[str] = []


@dataclass
class Point:
    x: float
    y: float


class UserDict(TypedDict):
    id: int
    name: str


def run_benchmark(name: str, func, iterations: int = 10_000) -> dict:
    for _ in range(100):
        func()

    start = time.perf_counter()
    for _ in range(iterations):
        func()
    total_time = time.perf_counter() - start

    ops_per_sec = iterations / total_time
    us_per_op = (total_time / iterations) * 1_000_000

    return {
        "Benchmark": name,
        "Iterations": iterations,
        "Total Time (s)": round(total_time, 4),
        "us/op": round(us_per_op, 2),
        "ops/sec": int(ops_per_sec),
    }


def main():
    print("=" * 60)
    print(" Typed Schema Validator - Performance Benchmark Suite ")
    print("=" * 60)

    user_payload = {"id": 1, "username": "alice_123", "email": "alice@example.com"}
    generic_payload = {
        "code": 200,
        "payload": {"id": 2, "username": "bob_456"},
        "tags": ["admin", "dev"],
    }
    point_payload = {"x": 10.5, "y": 20.0}
    dict_payload = {"id": 3, "name": "charlie"}

    user_instance = validate(User, user_payload)

    benchmarks = [
        ("Simple Schema Validation", lambda: validate(User, user_payload)),
        (
            "PEP 695 Generic Validation",
            lambda: validate(Response[User], generic_payload),
        ),
        ("Dataclass Validation", lambda: validate(Point, point_payload)),
        ("TypedDict Validation", lambda: validate(UserDict, dict_payload)),
        ("Model Dump (Serialization)", lambda: dump(user_instance)),
        (
            "JSON Schema Generation",
            lambda: to_json_schema(Response[User]),
        ),
    ]

    for name, fn in benchmarks:
        res = run_benchmark(name, fn)
        print(
            f"{res['Benchmark']:<30} | {res['us/op']:>7.2f} us/op | {res['ops/sec']:>10,d} ops/sec"
        )

    print("=" * 60)


if __name__ == "__main__":
    main()
