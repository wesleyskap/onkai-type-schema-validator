from typing import Any, Callable, Literal, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class ModelValidatorMarker:
    """Marker wrapper for methods decorated with @model_validator."""

    def __init__(
        self, func: Callable[..., Any], mode: Literal["before", "after"]
    ) -> None:
        self.func = func
        self.mode = mode

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


def model_validator(
    mode: Literal["before", "after"] = "after"
) -> Callable[[F], F]:
    """
    Decorator to mark a method as a model-level validator.

    - `mode="before"`: Runs on raw input dict before field validation.
    - `mode="after"`: Runs on validated Schema instance after field validation.

    Example:
        class Registration(Schema):
            password: str
            confirm_password: str

            @model_validator(mode="after")
            def check_passwords_match(self):
                if self.password != self.confirm_password:
                    raise ValueError("Passwords do not match")
                return self
    """

    def decorator(fn: F) -> F:
        marker = ModelValidatorMarker(fn, mode)
        return marker  # type: ignore

    return decorator
