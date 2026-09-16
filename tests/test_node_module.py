"""Tests for the node module methods (node_version, node_shutdown).

Mirrors the "node module" section of go-sdk/node/client_test.go.
"""

from __future__ import annotations

from mintlayer.node import Client


def test_node_version(rpc_server) -> None:
    srv = rpc_server(result="v0.9.7")
    client = Client(srv.url)
    assert client.node_version() == "v0.9.7"
    assert srv.capture.method == "node_version"
    assert srv.capture.params == {}
    client.close()


def test_node_shutdown(rpc_server) -> None:
    """A null result (void method) returns None."""
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.node_shutdown() is None
    assert srv.capture.method == "node_shutdown"
    assert srv.capture.params == {}
    client.close()
