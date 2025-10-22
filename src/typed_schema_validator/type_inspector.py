import functools
import inspect
import types
import typing
from typing import Any, get_args, get_origin


def is_pep695_alias(tp: Any) -> bool:
    """Check if tp is a PEP 695 type alias created with `type Alias[T] = ...`."""
    return isinstance(tp, typing.TypeAliasType)


def resolve_type_alias(
    tp: Any, type_args_map: dict[Any, Any] | None = None
) -> tuple[Any, dict[Any, Any]]:
    current_map = dict(type_args_map or {})
    if is_pep695_alias(tp):
        value = tp.__value__
        return value, current_map
    return tp, current_map


def get_type_params(target: Any) -> tuple[Any, ...]:
    """Extract PEP 695 type parameters from a class or alias."""
    if hasattr(target, "__type_params__"):
        return getattr(target, "__type_params__")
    return ()


@functools.lru_cache(maxsize=2048)
def build_type_var_map(generic_target: Any) -> tuple[Any, dict[Any, Any]]:
    """
    Given a target (which could be a specialized generic class like `User[int]`),
    returns the un-generic base class and a mapping of {TypeVar: ActualType}.
    """
    origin = get_origin(generic_target)
    if origin is None:
        return generic_target, {}

    args = get_args(generic_target)
    type_params = get_type_params(origin)

    mapping: dict[Any, Any] = {}
    if type_params and args:
        for param, arg in zip(type_params, args):
            mapping[param] = arg

    return origin, mapping


def substitute_typevars(tp: Any, type_var_map: dict[Any, Any]) -> Any:
    """Recursively substitute TypeVars in `tp` using `type_var_map`."""
    if not type_var_map:
        return tp

    if tp in type_var_map:
        return type_var_map[tp]

    if is_pep695_alias(tp):
        tp_val = tp.__value__
        return substitute_typevars(tp_val, type_var_map)

    origin = get_origin(tp)
    if origin is not None:
        args = get_args(tp)
        if args:
            new_args = tuple(substitute_typevars(arg, type_var_map) for arg in args)
            if origin is types.UnionType or origin is typing.Union:
                res = new_args[0]
                for extra in new_args[1:]:
                    res = res | extra
                return res
            try:
                return origin[*new_args]
            except Exception:
                try:
                    return origin[new_args]
                except Exception:
                    return tp
    return tp


def is_union_type(tp: Any) -> bool:
    origin = get_origin(tp)
    return origin is types.UnionType or origin is typing.Union


def get_union_args(tp: Any) -> tuple[Any, ...]:
    if is_union_type(tp):
        return get_args(tp)
    return ()


def is_optional_type(tp: Any) -> bool:
    if is_union_type(tp):
        args = get_args(tp)
        return type(None) in args
    return False
