"""Transport-level tests for the indexer REST client.

Mirrors the "Transport" and "HTTP error path" sections of
go-sdk/indexer/client_test.go, plus base-URL handling.
"""

from __future__ import annotations

import pytest
import requests

from mintlayer.indexer import Client, HTTPError, IndexerError


class TestClientConstruction:
    def test_defaults(self) -> None:
        client = Client("http://127.0.0.1:3000")
        assert client.api_base == "http://127.0.0.1:3000/api/v2"
        assert client.timeout == 30.0
        client.close()

    def test_timeout_parameter(self) -> None:
        client = Client("http://127.0.0.1:3000", timeout=5.0)
        assert client.timeout == 5.0
        client.close()

    def test_custom_session(self, rest_server) -> None:
        """A caller-supplied session is used for requests."""
        session = requests.Session()
        srv = rest_server(payload={"block_height": 1, "block_id": "x"})
        client = Client(srv.url, session=session)
        assert client._session is session
        assert client.get_tip().block_height == 1
        client.close()
        session.close()


def test_trailing_slash_trimmed(rest_server) -> None:
    """A trailing slash on the base URL must not produce a double slash."""
    srv = rest_server(payload="deadbeef0102")
    client = Client(srv.url + "/")
    assert client.get_block_id_at_height(1) == "deadbeef0102"
    assert srv.capture.path == "/api/v2/chain/1"
    client.close()


def test_paths_land_under_api_v2(rest_server) -> None:
    srv = rest_server(payload={"block_height": 123456, "block_id": "aabbccdd"})
    client = Client(srv.url)
    client.get_tip()
    assert srv.capture.path == "/api/v2/chain/tip"
    assert srv.capture.method == "GET"
    client.close()


def test_http_error_404(rest_server) -> None:
    srv = rest_server(raw='{"error":"NotFound"}\n', status=404)
    client = Client(srv.url)
    with pytest.raises(HTTPError) as excinfo:
        client.get_tip()
    err = excinfo.value
    assert err.status_code == 404
    assert err.body == '{"error":"NotFound"}'  # trailing newline trimmed
    client.close()


def test_http_error_500(rest_server) -> None:
    srv = rest_server(raw="internal error\n", status=500, content_type="text/plain; charset=utf-8")
    client = Client(srv.url)
    with pytest.raises(HTTPError) as excinfo:
        client.get_pool("mpool1abc")
    err = excinfo.value
    assert err.status_code == 500
    assert err.body == "internal error"
    assert str(err) == "HTTP 500: internal error"
    client.close()


def test_block_id_at_height_404(rest_server) -> None:
    """Unknown height -> HTTPError 404 (no JSON body)."""
    srv = rest_server(raw="not found\n", status=404)
    client = Client(srv.url)
    with pytest.raises(HTTPError) as excinfo:
        client.get_block_id_at_height(9999999)
    assert excinfo.value.status_code == 404
    assert excinfo.value.body == "not found"
    client.close()


def test_transaction_merkle_path_404(rest_server) -> None:
    """Merkle path is 404 until the transaction is included in a block."""
    srv = rest_server(raw='{"error":"NotFound"}', status=404)
    client = Client(srv.url)
    with pytest.raises(HTTPError) as excinfo:
        client.get_transaction_merkle_path("tx01")
    assert excinfo.value.status_code == 404
    client.close()


def test_invalid_json_raises_indexer_error(rest_server) -> None:
    """A 200 response with a non-JSON body raises IndexerError, not HTTPError."""
    srv = rest_server(raw="this is not json", status=200)
    client = Client(srv.url)
    with pytest.raises(IndexerError, match="decode response"):
        client.get_tip()
    client.close()
