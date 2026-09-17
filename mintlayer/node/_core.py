"""Shared result-decoding helpers for the node client mixins."""

from __future__ import annotations

from typing import Any

from mintlayer._jsonrpc import BaseJSONRPCClient, JSONRPCError

from .types import Amount


class _NodeCore(BaseJSONRPCClient):
    """Node-specific typed result helpers over the shared JSON-RPC base."""

    def _call_str(self, method: str, params: Any) -> str:
        result = self._rpc.call(method, params)
        if not isinstance(result, str):
            raise JSONRPCError(f"{method}: expected string result, got {result!r}")
        return result

    def _call_opt_str(self, method: str, params: Any) -> str | None:
        result = self._rpc.call(method, params)
        return None if result is None else str(result)

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
        return Amount.from_json(result) if result is not None else None
