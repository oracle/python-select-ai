# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

from typing import Any, Dict, Iterable, Literal, Optional, Sequence, Set, Tuple

import pytest

from select_ai._validations import _match, enforce_types

pytestmark = pytest.mark.unit


def test_4600_match_handles_any_optional_and_literal():
    assert _match("value", Any) is True
    assert _match(None, Optional[int]) is True
    assert _match("small", Literal["small", "large"]) is True
    assert _match("medium", Literal["small", "large"]) is False


def test_4601_match_handles_fixed_and_variadic_tuples():
    assert _match((1, "x"), Tuple[int, str]) is True
    assert _match((1, 2, 3), Tuple[int, ...]) is True
    assert _match((1, "x"), Tuple[int, int]) is False


def test_4602_match_handles_mappings_sequences_and_sets():
    assert _match({"a": 1}, Dict[str, int]) is True
    assert _match([1, 2, 3], Sequence[int]) is True
    assert _match({1, 2, 3}, Set[int]) is True
    assert _match("abc", Sequence[int]) is False


def test_4603_match_handles_plain_and_bare_container_types():
    assert _match(5, int) is True
    assert _match([1, 2], Iterable[int]) is True
    assert _match("five", int) is False


def test_4604_enforce_types_validates_sync_functions():
    @enforce_types
    def fn(name: str, count: int = 1):
        return f"{name}:{count}"

    assert fn("demo", 2) == "demo:2"
    with pytest.raises(TypeError):
        fn("demo", "two")


@pytest.mark.anyio
async def test_4605_enforce_types_validates_async_functions():
    @enforce_types
    async def fn(items: Sequence[int]):
        return sum(items)

    assert await fn([1, 2, 3]) == 6
    with pytest.raises(TypeError):
        await fn(["1"])

