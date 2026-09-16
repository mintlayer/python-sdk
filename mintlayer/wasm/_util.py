"""Shared helpers for public WASM client methods."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def synchronized(method: F) -> F:
    """Serialise a public method so the single WASM instance is never shared."""

    @functools.wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        with self.lock:
            return method(self, *args, **kwargs)

    return wrapper  # type: ignore[return-value]


def bool_to_int(b: bool) -> int:
    """Encode a Python bool as the WASM ABI's 0/1."""
    return 1 if b else 0
