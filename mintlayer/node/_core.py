"""Shared result-decoding helpers for the node client mixins."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from mintlayer._jsonrpc import BaseJSONRPCClient, JSONRPCError

from .types import Amount

_T = TypeVar("_T")


def _decode_model(method: str, factory: Callable[[Any], _T], data: Any) -> _T:
    """Run a ``from_json`` decoder, converting malformed payloads to the
    documented JSONRPCError contract (mirrors the indexer's _safe_from_json).
    """
    try:
        return factory(data)
    except JSONRPCError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise JSONRPCError(f"{method}: malformed result ({exc!r})") from exc


class _NodeCore(BaseJSONRPCClient):
    """Node-specific typed result helpers over the shared JSON-RPC base."""

    def _call_str(self, method: str, params: Any) -> str:
        result = self._rpc.call(method, params)
        if not isinstance(result, str):
            raise JSONRPCError(f"{method}: expected string result, got {result!r}")
        return result

    def _call_opt_str(self, method: str, params: Any) -> str | None:
        result = self._rpc.call(method, params)
        if result is None:
            return None
        if not isinstance(result, str):
            # Coercing a dict/number to str would return garbage silently.
            raise JSONRPCError(f"{method}: expected string result, got {result!r}")
        return result

    def _call_int(self, method: str, params: Any) -> int:
        result = self._rpc.call(method, params)
        if isinstance(result, bool) or not isinstance(result, int):
            raise JSONRPCError(f"{method}: expected integer result, got {result!r}")
        return result

    def _call_opt_int(self, method: str, params: Any) -> int | None:
        result = self._rpc.call(method, params)
        if result is None:
            return None
        if isinstance(result, bool) or not isinstance(result, int):
            raise JSONRPCError(f"{method}: expected integer result, got {result!r}")
        return result

    def _call_bool(self, method: str, params: Any) -> bool:
        result = self._rpc.call(method, params)
        if not isinstance(result, bool):
            raise JSONRPCError(f"{method}: expected boolean result, got {result!r}")
        return result

    def _call_str_list(self, method: str, params: Any) -> list[str]:
        result = self._rpc.call(method, params)
        if result is None:
            return []
        if not isinstance(result, list) or not all(isinstance(item, str) for item in result):
            raise JSONRPCError(f"{method}: expected list of strings, got {result!r}")
        return result

    def _call_opt_amount(self, method: str, params: Any) -> Amount | None:
        result = self._rpc.call(method, params)
        if result is None:
            return None
        # Amount.from_json raises bare ValueError/KeyError; decoding failures
        # must surface as the documented JSONRPCError contract.
        return _decode_model(method, Amount.from_json, result)
