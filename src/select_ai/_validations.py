# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import inspect
from collections.abc import Mapping, Sequence, Set
from functools import wraps
from typing import Any, get_args, get_origin, get_type_hints

NoneType = type(None)


def _match(value, annot) -> bool:
    """Recursively validate value against a typing annotation."""
    if annot is Any:
        return True

    origin = get_origin(annot)
    args = get_args(annot)

    # Handle Annotated[T, ...] → treat as T
    if origin is getattr(__import__("typing"), "Annotated", None):
        annot = args[0]
        origin = get_origin(annot)
        args = get_args(annot)

    # Optional[T] is Union[T, NoneType]
    if origin is getattr(__import__("typing"), "Union", None):
        return any(_match(value, a) for a in args)

    # Literal[…]
    if origin is getattr(__import__("typing"), "Literal", None):
        return any(value == lit for lit in args)

    # Tuple cases
    if origin is tuple:
        if not isinstance(value, tuple):
            return False
        if len(args) == 2 and args[1] is Ellipsis:
            # tuple[T, ...]
            return all(_match(v, args[0]) for v in value)
        if len(args) != len(value):
            return False
        return all(_match(v, a) for v, a in zip(value, args))

    # Mappings (dict-like)
    if origin in (dict, Mapping):
        if not isinstance(value, Mapping):
            return False
        k_annot, v_annot = args if args else (Any, Any)
        return all(
            _match(k, k_annot) and _match(v, v_annot) for k, v in value.items()
        )

    # Sequences (list, Sequence) – but not str/bytes
    if origin in (list, Sequence):
        if isinstance(value, (str, bytes)):
            return False
        if not isinstance(value, Sequence):
            return False
        elem_annot = args[0] if args else Any
        return all(_match(v, elem_annot) for v in value)

    # Sets
    if origin in (set, frozenset, Set):
        if not isinstance(value, (set, frozenset)):
            return False
        elem_annot = args[0] if args else Any
        return all(_match(v, elem_annot) for v in value)

    # Fall back to normal isinstance for non-typing classes
    if isinstance(annot, type):
        return isinstance(value, annot)

    # If annot is a typing alias like 'list' without args
    if origin is not None:
        # Treat bare containers as accepting anything inside
        return isinstance(value, origin)

    # Unknown/unsupported typing form: accept conservatively
    return True


def enforce_types(func):
    # Resolve ForwardRefs using function globals (handles "User" as a string, etc.)
    hints = get_type_hints(
        func, globalns=func.__globals__, include_extras=True
    )
    sig = inspect.signature(func)

    def _check(bound):
        for name, val in bound.arguments.items():
            if name in hints:
                annot = hints[name]
                if not _match(val, annot):
                    raise TypeError(
                        f"Argument '{name}' failed type check: expected {annot!r}, "
                        f"got {type(val).__name__} -> {val!r}"
                    )

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def aw(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            _check(bound)
            return await func(*args, **kwargs)

        return aw
    else:

        @wraps(func)
        def w(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            _check(bound)
            return func(*args, **kwargs)

        return w
