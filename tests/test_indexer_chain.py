"""Tests for the indexer chain endpoints.

Mirrors the "Chain (3b)" section of go-sdk/indexer/client_test.go.
"""

from __future__ import annotations

from mintlayer.indexer import ChainTip, Client, GenesisInfo
from mintlayer.indexer.types import Timestamp  # not re-exported by the package


def test_get_tip(rest_server) -> None:
    srv = rest_server(payload={"block_height": 123456, "block_id": "aabbccdd"})
    client = Client(srv.url)
    tip = client.get_tip()
    assert isinstance(tip, ChainTip)
    assert tip.block_height == 123456
    assert tip.block_id == "aabbccdd"
    assert srv.capture.path == "/api/v2/chain/tip"
    client.close()


def test_get_genesis(rest_server) -> None:
    """The genesis timestamp is a nested ``{"timestamp": <unix seconds>}``."""
    srv = rest_server(
        payload={
            "block_id": "genesisid",
            "genesis_message": "mintlayer",
            "timestamp": {"timestamp": 1700000000},
        }
    )
    client = Client(srv.url)
    genesis = client.get_genesis()
    assert isinstance(genesis, GenesisInfo)
    assert genesis.block_id == "genesisid"
    assert genesis.genesis_message == "mintlayer"
    assert genesis.timestamp == Timestamp(timestamp=1700000000)
    assert genesis.timestamp.timestamp == 1700000000
    assert srv.capture.path == "/api/v2/chain/genesis"
    client.close()


def test_get_block_id_at_height(rest_server) -> None:
    """The endpoint returns a bare JSON string block ID."""
    srv = rest_server(payload="deadbeef0102")
    client = Client(srv.url)
    assert client.get_block_id_at_height(100000) == "deadbeef0102"
    assert srv.capture.path == "/api/v2/chain/100000"
    client.close()


def test_get_block_id_at_height_null(rest_server) -> None:
    """A JSON null body maps to None (optional str, not the empty string)."""
    srv = rest_server(payload=None)
    client = Client(srv.url)
    assert client.get_block_id_at_height(100000) is None
    assert srv.capture.path == "/api/v2/chain/100000"
    client.close()


def test_get_block_id_at_height_path_contains_height(rest_server) -> None:
    srv = rest_server(payload="aabb")
    client = Client(srv.url)
    client.get_block_id_at_height(12345)
    assert srv.capture.path.endswith("/chain/12345")
    assert "12345" in srv.capture.path
    client.close()
