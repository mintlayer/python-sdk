"""Transport-level tests for the wallet client.

Mirrors the "Transport" and "Error path" sections of
go-sdk/wallet/client_test.go: basic auth, JSON-RPC error objects, and
monotonically increasing request ids.
"""

from __future__ import annotations

import base64
import json

import pytest

from mintlayer.wallet import BestBlock, Client, RPCError

_BLOCK_RESULT = {"height": 100, "id": "aabbccdd"}


class TestClientConstruction:
    def test_defaults(self) -> None:
        client = Client("http://127.0.0.1:3034")
        assert client._rpc.endpoint == "http://127.0.0.1:3034"
        assert client._rpc.username == ""
        assert client._rpc.password == ""
        assert client._rpc.timeout == 30.0
        client.close()

    def test_timeout_parameter(self) -> None:
        client = Client("http://127.0.0.1:3034", timeout=5.0)
        assert client._rpc.timeout == 5.0
        client.close()


def test_basic_auth_header(rpc_server) -> None:
    """The Authorization header is sent when a username is set."""
    srv = rpc_server(result=_BLOCK_RESULT)
    client = Client(srv.url, username="alice", password="secret")
    assert client.best_block() == BestBlock(height=100, id="aabbccdd")
    expected = "Basic " + base64.b64encode(b"alice:secret").decode("ascii")
    assert srv.capture.headers.get("authorization") == expected
    client.close()


def test_no_auth_header_without_username(rpc_server) -> None:
    """No Authorization header when the username is empty."""
    srv = rpc_server(result=_BLOCK_RESULT)
    client = Client(srv.url)
    client.best_block()
    assert "authorization" not in srv.capture.headers
    client.close()


def test_rpc_error(rpc_server) -> None:
    """A JSON-RPC error object in the body raises RPCError."""
    srv = rpc_server(error=(-32601, "method not found"))
    client = Client(srv.url)
    with pytest.raises(RPCError) as excinfo:
        client.best_block()
    err = excinfo.value
    assert err.code == -32601
    assert err.message == "method not found"
    assert str(err) == "RPC error -32601: method not found"
    client.close()


def test_request_wire_shape(rpc_server) -> None:
    """Requests POST the full JSON-RPC 2.0 envelope straight to the endpoint."""
    srv = rpc_server(result=_BLOCK_RESULT)
    client = Client(srv.url)
    client.best_block()
    assert srv.capture.method == "wallet_best_block"
    assert srv.capture.params == {}
    assert srv.capture.path == "/"
    assert srv.capture.request_count == 1
    assert json.loads(srv.capture.raw_body) == {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "wallet_best_block",
        "params": {},
    }
    client.close()


def test_request_ids_monotonic(rpc_server) -> None:
    srv = rpc_server(result=_BLOCK_RESULT)
    client = Client(srv.url)
    client.best_block()
    client.best_block()
    assert [payload["id"] for payload in srv.capture.payloads] == [1, 2]
    client.close()


def test_context_manager_calls_close(rpc_server, monkeypatch) -> None:
    srv = rpc_server(result=_BLOCK_RESULT)
    client = Client(srv.url)
    closed: list[bool] = []
    monkeypatch.setattr(client, "close", lambda: closed.append(True))
    with client as entered:
        assert entered is client
        entered.best_block()
    assert closed == [True]
