"""Shared result-decoding helpers for the node client mixins."""

from __future__ import annotations

from typing import Any

from mintlayer._jsonrpc import JSONRPCClient, JSONRPCError


class _NodeCore:
    """Thin wrapper over the JSON-RPC transport with typed result helpers."""

    _rpc: JSONRPCClient

    def _call(self, method: str, params: Any) -> Any:
        """Call and return the decoded JSON result (None for JSON null)."""
        return self._rpc.call(method, params)

    def _call_ignore(self, method: str, params: Any) -> None:
        """Call and discard the result (void methods)."""
        self._rpc.call(method, params)

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
        return None if result is None else int(result)

    def _call_bool(self, method: str, params: Any) -> bool:
        result = self._rpc.call(method, params)
        if not isinstance(result, bool):
            raise JSONRPCError(f"{method}: expected boolean result, got {result!r}")
        return result

    def _call_str_list(self, method: str, params: Any) -> list[str]:
        result = self._rpc.call(method, params)
        return [str(item) for item in result or []]

    def _call_opt_amount(self, method: str, params: Any) -> Any:
        from .types import Amount

        result = self._rpc.call(method, params)
        return Amount.from_json(result) if result is not None else None

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._rpc.close()
