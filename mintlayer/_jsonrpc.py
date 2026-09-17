"""Shared JSON-RPC 2.0 transport for the node and wallet clients.

Mirrors the (duplicated) transports in go-sdk/node/client.go and
go-sdk/wallet/client.go:

* one HTTP POST per call, no batching, params are always a JSON object
  (``{}`` for no-arg methods),
* monotonically increasing integer request IDs starting at 1,
* HTTP Basic Auth applied only when a username is set (and never sourced
  from the environment — ``.netrc`` lookup is suppressed for sessions the
  client creates itself; caller-supplied sessions keep their own
  ``trust_env`` behavior),
* no per-call cancellation: timeouts are configured on the client
  (Go's per-call ``context`` has no direct requests equivalent),
* the HTTP status code is never inspected — a JSON-RPC ``error`` object in the
  body is the error contract,
* JSON ``null`` results signal "not found" for pointer-returning methods.
"""

from __future__ import annotations

import threading
from typing import Any

import requests

__all__ = ["JSONRPCError", "RPCError", "JSONRPCClient"]


class _NoAuth(requests.auth.AuthBase):
    """Explicit no-auth marker; prevents requests' .netrc environment fallback."""

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        return r


class JSONRPCError(Exception):
    """Transport or codec failure (not a JSON-RPC error object)."""


class RPCError(Exception):
    """JSON-RPC error returned by the daemon."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"RPC error {code}: {message}")
        self.code = code
        self.message = message


class JSONRPCClient:
    """Minimal JSON-RPC 2.0 over HTTP POST client."""

    def __init__(
        self,
        endpoint: str,
        username: str = "",
        password: str = "",
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.timeout = timeout
        self._owns_session = session is None
        self._session = session if session is not None else requests.Session()
        self._lock = threading.Lock()
        self._id = 0

    def call(self, method: str, params: Any) -> Any:
        """Execute a JSON-RPC call and return the parsed result.

        ``params`` must be a JSON-serialisable object (dict); no-arg methods
        pass ``{}``. A JSON-RPC error object raises :class:`RPCError`.
        """
        with self._lock:
            self._id += 1
            request_id = self._id
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        if self.username:
            auth: requests.auth.AuthBase | tuple[str, str] | None = (self.username, self.password)
        elif self._owns_session:
            auth = _NoAuth()
        else:
            auth = None
        try:
            resp = self._session.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout,
                auth=auth,
                headers={"Content-Type": "application/json"},
            )
        except requests.RequestException as exc:
            raise JSONRPCError(f"http request: {exc}") from exc
        try:
            body = resp.json()
        except ValueError as exc:
            raise JSONRPCError(f"decode response: {exc}") from exc
        if not isinstance(body, dict):
            raise JSONRPCError("decode response: unexpected JSON-RPC response shape")
        error = body.get("error")
        if error is not None:
            if not isinstance(error, dict):
                raise JSONRPCError("decode response: JSON-RPC error object has unexpected shape")
            raise RPCError(error.get("code", 0), error.get("message", ""))
        return body.get("result")

    def close(self) -> None:
        """Close the HTTP session (only if the client created it)."""
        if self._owns_session:
            self._session.close()


class BaseJSONRPCClient:
    """Mixin base shared by the node and wallet clients.

    Both clients wrap a :class:`JSONRPCClient` as ``self._rpc`` and share the
    raw-call and session-lifecycle helpers below. Typed result decoding stays
    in each package's ``_core`` module (mirroring the separate Go node/wallet
    packages).
    """

    _rpc: JSONRPCClient

    def _call(self, method: str, params: Any) -> Any:
        """Call and return the decoded JSON result (None for JSON null)."""
        return self._rpc.call(method, params)

    def _call_ignore(self, method: str, params: Any) -> None:
        """Call and discard the result (void methods)."""
        self._rpc.call(method, params)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._rpc.close()
