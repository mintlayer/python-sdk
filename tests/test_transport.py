"""Transport-level tests: client construction, auth, errors, and wire shape.

Mirrors the "Transport" and "Error path" sections of go-sdk/node/client_test.go.
"""

from __future__ import annotations

import base64
import json

import pytest

from mintlayer.node import Client, RPCError

_DUMMY_ENDPOINT = "http://127.0.0.1:3030"


class TestClientConstruction:
    def test_defaults(self) -> None:
        client = Client(_DUMMY_ENDPOINT)
        assert client._rpc.endpoint == _DUMMY_ENDPOINT
        assert client._rpc.username == ""
        assert client._rpc.password == ""
        assert client._rpc.timeout == 30.0
        client.close()

    def test_timeout_parameter(self) -> None:
        client = Client(_DUMMY_ENDPOINT, timeout=5.0)
        assert client._rpc.timeout == 5.0
        client.close()


def test_basic_auth_header(rpc_server) -> None:
    """The Authorization header is sent when a username is set."""
    srv = rpc_server(result="1.0.0")
    client = Client(srv.url, username="alice", password="secret")
    assert client.node_version() == "1.0.0"
    expected = "Basic " + base64.b64encode(b"alice:secret").decode("ascii")
    assert srv.capture.headers.get("authorization") == expected
    client.close()


def test_no_auth_header_without_username(rpc_server) -> None:
    """No Authorization header when the username is empty."""
    srv = rpc_server(result="1.0.0")
    client = Client(srv.url)
    assert client.node_version() == "1.0.0"
    assert "authorization" not in srv.capture.headers
    client.close()


def test_rpc_error(rpc_server) -> None:
    srv = rpc_server(error=(-32601, "method not found"))
    client = Client(srv.url)
    with pytest.raises(RPCError) as excinfo:
        client.node_version()
    err = excinfo.value
    assert err.code == -32601
    assert err.message == "method not found"
    assert str(err) == "RPC error -32601: method not found"
    client.close()


def test_request_wire_shape(rpc_server) -> None:
    """Requests POST the full JSON-RPC 2.0 envelope straight to the endpoint."""
    srv = rpc_server(result="ok")
    client = Client(srv.url)
    client.node_version()
    assert srv.capture.method == "node_version"
    assert srv.capture.params == {}
    assert srv.capture.path == "/"
    assert srv.capture.request_count == 1
    assert json.loads(srv.capture.raw_body) == {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "node_version",
        "params": {},
    }
    client.close()


def test_request_ids_increment(rpc_server) -> None:
    srv = rpc_server(result="ok")
    client = Client(srv.url)
    client.node_version()
    client.node_version()
    assert [payload["id"] for payload in srv.capture.payloads] == [1, 2]
    client.close()
