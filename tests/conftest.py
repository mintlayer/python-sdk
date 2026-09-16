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
* :func:`make_rest_server` -- plain REST server for the indexer client:
  answers GET *and* POST with a canned JSON payload (or verbatim raw text),
  any HTTP status, and records the HTTP verb, path, query string, headers,
  and raw body on a :class:`RESTCapture`.

Prefer the :func:`rpc_server` fixture: it is a factory that starts servers
(threading daemons) and guarantees shutdown in teardown. The indexer REST
tests use the :func:`rest_server` factory fixture, which works the same way.
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


# --- REST servers (indexer client) -------------------------------------------


class RESTCapture(Capture):
    """Capture for the REST servers.

    The inherited ``method`` field holds the *HTTP verb* (``"GET"`` /
    ``"POST"``), ``path`` the path *without* the query string, and ``query``
    the raw query string (``""`` when absent). ``raw_body`` carries the
    verbatim request body (empty for GET).
    """

    def __init__(self) -> None:
        super().__init__()
        self.query: str | None = None
        self.verbs: list[str] = []
        self.paths: list[str] = []
        self.queries: list[str] = []

    def record_rest(
        self,
        *,
        verb: str,
        path: str,
        query: str,
        headers: dict[str, str],
        raw_body: bytes,
    ) -> None:
        with self._lock:
            self.method = verb
            self.params = None
            self.headers = dict(headers)
            self.path = path
            self.query = query
            self.raw_body = raw_body
            self.request_count += 1
            self.request_ids.append(None)
            self.payloads.append({})
            self.verbs.append(verb)
            self.paths.append(path)
            self.queries.append(query)


def _make_rest_handler(capture: RESTCapture, body: bytes, status: int, content_type: str):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _handle(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            raw_body = self.rfile.read(length) if length else b""
            path, _, query = self.path.partition("?")
            capture.record_rest(
                verb=self.command,
                path=path,
                query=query,
                headers={str(k).lower(): str(v) for k, v in self.headers.items()},
                raw_body=raw_body,
            )
            self._respond(status, body)

        do_GET = _handle
        do_POST = _handle

        def _respond(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass  # keep test output clean

    return Handler


def make_rest_server(
    payload: Any = None,
    *,
    raw: str | bytes | None = None,
    status: int = 200,
    content_type: str = "application/json",
) -> ServerHandle:
    """Start a REST server answering every GET/POST identically.

    ``payload`` is JSON-encoded; ``raw`` (string or bytes) is served verbatim
    instead, pinning exact wire shapes. ``status`` may be any code, e.g. 404
    or 500, to exercise the error paths. Prefer the :func:`rest_server`
    fixture so servers are always stopped.
    """
    if raw is not None:
        body = raw if isinstance(raw, bytes) else str(raw).encode("utf-8")
    else:
        body = json.dumps(payload).encode("utf-8")
    capture = RESTCapture()
    httpd = ThreadingHTTPServer((_HOST, 0), _make_rest_handler(capture, body, status, content_type))
    thread = threading.Thread(
        target=httpd.serve_forever,
        daemon=True,
        name="rest-test-server",
    )
    thread.start()
    return ServerHandle(httpd=httpd, capture=capture, thread=thread)


@pytest.fixture
def rest_server():
    """Factory fixture that starts/stops in-process REST test servers.

    Usage::

        srv = rest_server(payload={"block_height": 1})
        client = indexer.Client(srv.url)
        client.get_tip()
        assert srv.capture.path == "/api/v2/chain/tip"

    Keyword alternatives: ``raw="<text>"`` to serve a verbatim body, ``status``
    for arbitrary HTTP status codes (404/500), and ``content_type`` to pin the
    response Content-Type. Every server started through the factory is shut
    down in teardown.
    """
    handles: list[ServerHandle] = []

    def _start(
        payload: Any = None,
        *,
        raw: str | bytes | None = None,
        status: int = 200,
        content_type: str = "application/json",
    ) -> ServerHandle:
        handle = make_rest_server(payload, raw=raw, status=status, content_type=content_type)
        handles.append(handle)
        return handle

    yield _start

    for handle in handles:
        handle.stop()
