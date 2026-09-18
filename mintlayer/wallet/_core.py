"""Shared result-decoding helpers for the wallet client mixins."""

from __future__ import annotations

from typing import Any, TypeVar

from mintlayer._jsonrpc import BaseJSONRPCClient, JSONRPCError

_T = TypeVar("_T")


class _WalletCore(BaseJSONRPCClient):
    """Wallet-specific typed result helpers over the shared JSON-RPC base."""

    def _call_model(self, method: str, params: Any, cls: type[_T]) -> _T:
        data = self._rpc.call(method, params)
        if data is None:
            raise JSONRPCError(f"{method}: expected object result, got null")
        return cls.from_json(data)  # type: ignore[attr-defined]

    def _call_model_list(self, method: str, params: Any, cls: type[_T]) -> list[_T]:
        data = self._rpc.call(method, params)
        if data is None:
            return []  # JSON null == empty list (matches Go's nil-slice decode)
        if not isinstance(data, list):
            raise JSONRPCError(f"{method}: expected list result, got {data!r}")
        return [cls.from_json(item) for item in data]  # type: ignore[attr-defined]
