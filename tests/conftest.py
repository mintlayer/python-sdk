"""In-process JSON-RPC test servers for the Mintlayer node client tests.

Mirrors the httptest helpers in go-sdk/node/client_test.go, using the stdlib
``http.server`` + threading instead of httptest:

* :func:`make_rpc_server` -- answers every JSON-RPC POST with
  ``{"jsonrpc": "2.0", "id": <echoed id>, "result": <canned result>}``.
  ``result=None`` produces a JSON ``null`` result (void / not-found methods).
* :func:`make_rpc_error_server` -- answers with a JSON-RPC error object.
* :func:`make_raw_rpc_server` -- embeds raw JSON *text* verbatim as the
  result, pinning exact wire shapes (mirrors Go's ``json.RawMessage``).
* :class:`Capture` -- records the last request (method name, params, headers,
  path, raw body, request count) plus every echoed request id, so tests can
  pin exact wire shapes.

Prefer the :func:`rpc_server` fixture: it is a factory that starts servers
(threading daemons) and guarantees shutdown in teardown.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

_HOST = "127.0.0.1"


class Capture:
    """Thread-safe recorder for the requests hitting a test server."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Last request seen.
        self.method: str | None = None
        self.params: Any = None
        self.headers: dict[str, str] = {}
        self.path: str | None = None
        self.raw_body: bytes | None = None
        # All requests seen.
        self.request_count = 0
        self.request_ids: list[Any] = []
        self.payloads: list[dict[str, Any]] = []
        self.protocol_errors: list[str] = []

    def record(
        self,
        *,
        method: str | None,
        params: Any,
        headers: dict[str, str],
        path: str | None,
        raw_body: bytes,
        request_id: Any,
        payload: dict[str, Any],
    ) -> None:
        with self._lock:
            self.method = method
            self.params = params
            self.headers = dict(headers)
            self.path = path
            self.raw_body = raw_body
            self.request_count += 1
            self.request_ids.append(request_id)
            self.payloads.append(payload)

    def record_protocol_error(self, message: str) -> None:
        with self._lock:
            self.protocol_errors.append(message)


def _result_responder(result: Any):
    def respond(payload: dict[str, Any]) -> tuple[int, Any]:
        return 200, {"jsonrpc": "2.0", "id": payload.get("id"), "result": result}

    return respond


def _error_responder(code: int, message: str):
    def respond(payload: dict[str, Any]) -> tuple[int, Any]:
        return 200, {
            "jsonrpc": "2.0",
            "id": payload.get("id"),
            "error": {"code": code, "message": message},
        }

    return respond


def _raw_responder(raw_result: str):
    def respond(payload: dict[str, Any]) -> tuple[int, Any]:
        body = f'{{"jsonrpc":"2.0","id":{json.dumps(payload.get("id"))},"result":{raw_result}}}'
        return 200, body.encode("utf-8")

    return respond


class ServerHandle:
    """A running in-process JSON-RPC server plus its request capture."""

    def __init__(
        self,
        httpd: ThreadingHTTPServer,
        capture: Capture,
        thread: threading.Thread,
    ) -> None:
        self.httpd = httpd
        self.capture = capture
        self._thread = thread

    @property
    def url(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}"

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self._thread.join(timeout=5)


def _make_handler(capture: Capture, responder):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            raw_body = self.rfile.read(length)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except ValueError:
                capture.record_protocol_error("request body is not valid JSON")
                self._respond(400, b"bad request")
                return
            if payload.get("jsonrpc") != "2.0":
                capture.record_protocol_error(
                    f"expected jsonrpc 2.0, got {payload.get('jsonrpc')!r}"
                )
                self._respond(400, b"bad request")
                return
            capture.record(
                method=payload.get("method"),
                params=payload.get("params"),
                headers={str(k).lower(): str(v) for k, v in self.headers.items()},
                path=self.path,
                raw_body=raw_body,
                request_id=payload.get("id"),
                payload=payload,
            )
            status, body = responder(payload)
            encoded = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            self._respond(status, encoded)

        def _respond(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass  # keep test output clean

    return Handler


def _start_server(capture: Capture, responder) -> ServerHandle:
    httpd = ThreadingHTTPServer((_HOST, 0), _make_handler(capture, responder))
    thread = threading.Thread(
        target=httpd.serve_forever,
        daemon=True,
        name="json-rpc-test-server",
    )
    thread.start()
    return ServerHandle(httpd=httpd, capture=capture, thread=thread)


def make_rpc_server(result: Any = None) -> ServerHandle:
    """Start a server answering every JSON-RPC POST with ``result``.

    ``result=None`` produces a JSON ``null`` result (void / not-found methods).
    Prefer the :func:`rpc_server` fixture so servers are always stopped.
    """
    return _start_server(Capture(), _result_responder(result))


def make_rpc_error_server(code: int, message: str) -> ServerHandle:
    """Start a server answering every JSON-RPC POST with an error object."""
    return _start_server(Capture(), _error_responder(code, message))


def make_raw_rpc_server(raw_result: str) -> ServerHandle:
    """Start a server embedding ``raw_result`` verbatim as the JSON-RPC result."""
    return _start_server(Capture(), _raw_responder(raw_result))


@pytest.fixture
def rpc_server():
    """Factory fixture that starts/stops in-process JSON-RPC test servers.

    Usage::

        srv = rpc_server(result={"atoms": "1"})
        client = Client(srv.url)   # srv.url is the base URL
        ...
        srv.capture.method         # last request's method name

    Keyword alternatives: ``error=(code, message)`` for a JSON-RPC error
    server and ``raw="<json text>"`` to pin an exact wire shape. Every server
    started through the factory is shut down in teardown.
    """
    handles: list[ServerHandle] = []

    def _start(
        *,
        result: Any = None,
        error: tuple[int, str] | None = None,
        raw: str | None = None,
    ) -> ServerHandle:
        if error is not None:
            handle = make_rpc_error_server(*error)
        elif raw is not None:
            handle = make_raw_rpc_server(raw)
        else:
            handle = make_rpc_server(result)
        handles.append(handle)
        return handle

    yield _start

    for handle in handles:
        handle.stop()
