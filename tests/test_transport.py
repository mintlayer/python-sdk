"""Transport-level tests: client construction, auth, errors, and wire shape.

Mirrors the "Transport" and "Error path" sections of go-sdk/node/client_test.go.
"""

from __future__ import annotations

import base64
import json

import pytest

from mintlayer._jsonrpc import JSONRPCClient, JSONRPCError
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


def test_response_id_mismatch_raises(rpc_server) -> None:
    """A response belonging to another call is not silently misattributed.

    ``rpc_server(raw=...)`` -> ``make_raw_rpc_server`` splices its text
    verbatim after ``"result":``, so the text ``1,"id":999`` adds a second
    id key that ``json`` keeps (last one wins). The parsed response id is
    999 while this fresh client's first request id is 1.
    """
    srv = rpc_server(raw='1,"id":999')
    client = JSONRPCClient(srv.url)
    with pytest.raises(JSONRPCError, match="response id mismatch: expected 1, got 999"):
        client.call("node_version", {})
    client.close()


def test_response_null_id_raises(rpc_server) -> None:
    """A JSON null response id (server-side notification) cannot be
    attributed to this call and must fail loudly.

    ``rpc_server(raw=...)`` -> ``make_raw_rpc_server`` splices its text
    verbatim after ``"result":``, so the text ``1,"id":null`` adds a second
    id key that ``json`` keeps (last one wins). The parsed response id is
    ``None`` while this fresh client's first request id is 1.
    """
    srv = rpc_server(raw='1,"id":null')
    client = JSONRPCClient(srv.url)
    with pytest.raises(JSONRPCError, match="response id mismatch: expected 1, got None"):
        client.call("node_version", {})
    client.close()


class TestCredentialSafetyGuard:
    """Basic-auth credentials must not go over cleartext http to remote hosts.

    The guard fires in ``JSONRPCClient.__init__``, before any network I/O.
    """

    def test_cleartext_http_nonloopback_with_username_raises(self) -> None:
        with pytest.raises(ValueError, match="basic-auth") as excinfo:
            JSONRPCClient("http://example.com:7103", username="user")
        assert "example.com" in str(excinfo.value)

    def test_cleartext_http_loopback_ipv4_allowed(self) -> None:
        client = JSONRPCClient("http://127.0.0.1:7103", username="user", password="pw")
        client.close()

    @pytest.mark.parametrize(
        "endpoint",
        [
            pytest.param("http://localhost:7103", id="localhost"),
            pytest.param("http://[::1]:7103", id="ipv6_loopback"),
        ],
    )
    def test_cleartext_http_loopback_hosts_allowed(self, endpoint: str) -> None:
        client = JSONRPCClient(endpoint, username="user")
        client.close()

    def test_https_nonloopback_with_username_allowed(self) -> None:
        client = JSONRPCClient("https://example.com", username="user")
        client.close()

    def test_cleartext_http_without_username_allowed(self) -> None:
        client = JSONRPCClient("http://example.com")
        client.close()
