"""Shared result-decoding helpers for the wallet client mixins."""

from __future__ import annotations

from typing import Any, TypeVar

from mintlayer._jsonrpc import JSONRPCClient, JSONRPCError

_T = TypeVar("_T")


class _WalletCore:
    """Thin wrapper over the JSON-RPC transport with typed result helpers."""

    _rpc: JSONRPCClient

    def _call(self, method: str, params: Any) -> Any:
        return self._rpc.call(method, params)

    def _call_ignore(self, method: str, params: Any) -> None:
        self._rpc.call(method, params)

    def _call_model(self, method: str, params: Any, cls: type[_T]) -> _T:
        data = self._rpc.call(method, params)
        if data is None:
            raise JSONRPCError(f"{method}: expected object result, got null")
        return cls.from_json(data)  # type: ignore[attr-defined]

    def _call_model_list(self, method: str, params: Any, cls: type[_T]) -> list[_T]:
        data = self._rpc.call(method, params)
        return [cls.from_json(item) for item in data or []]  # type: ignore[attr-defined]

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._rpc.close()
