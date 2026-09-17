"""Tests for the indexer transaction endpoints.

Mirrors the "Transaction (3d)" section of go-sdk/indexer/client_test.go,
including pagination, zero-value PageOpts, and the text/plain submit route.
"""

from __future__ import annotations

import pytest

from mintlayer.indexer import Client, IndexerError, MerklePath, PageOpts, Transaction


def test_list_transactions_pagination(rest_server) -> None:
    srv = rest_server(payload=[])
    client = Client(srv.url)
    assert client.list_transactions(PageOpts(offset=10, items=20)) == []
    assert srv.capture.path == "/api/v2/transaction"
    assert "offset=10" in srv.capture.query
    assert "items=20" in srv.capture.query
    client.close()


def test_list_transactions_zero_page_opts_no_params(rest_server) -> None:
    """Zero PageOpts sends NO offset/items params (server defaults apply)."""
    srv = rest_server(payload=[])
    client = Client(srv.url)
    client.list_transactions(PageOpts())
    assert "offset" not in srv.capture.query
    assert "items" not in srv.capture.query
    assert srv.capture.query == ""
    client.close()


def test_list_transactions_decodes_entries(rest_server) -> None:
    srv = rest_server(
        payload=[
            {
                "id": "tx01",
                "block_id": "block01",
                "timestamp": "1700000000",
                "confirmations": "10",
            }
        ]
    )
    client = Client(srv.url)
    txs = client.list_transactions(PageOpts(offset=0, items=5))
    assert len(txs) == 1
    assert isinstance(txs[0], Transaction)
    assert txs[0].id == "tx01"
    assert "items=5" in srv.capture.query
    assert "offset" not in srv.capture.query  # zero offset omitted
    client.close()


def test_get_transaction(rest_server) -> None:
    srv = rest_server(
        payload={
            "id": "aabbccdd",
            "block_id": "blockid01",
            "timestamp": "1700000000",
            "confirmations": "100",
        }
    )
    client = Client(srv.url)
    tx = client.get_transaction("aabbccdd")
    assert isinstance(tx, Transaction)
    assert tx.id == "aabbccdd"
    assert tx.block_id == "blockid01"
    assert tx.timestamp == "1700000000"
    assert tx.confirmations == "100"
    assert srv.capture.path == "/api/v2/transaction/aabbccdd"
    client.close()


def test_get_transaction_unconfirmed(rest_server) -> None:
    """Block ID / timestamp / confirmations default to empty strings."""
    srv = rest_server(payload={"id": "pending01"})
    client = Client(srv.url)
    tx = client.get_transaction("pending01")
    assert tx.block_id == ""
    assert tx.timestamp == ""
    assert tx.confirmations == ""
    client.close()


def test_get_transaction_merkle_path(rest_server) -> None:
    srv = rest_server(
        payload={
            "block_id": "block01",
            "transaction_index": 3,
            "merkle_root": "root01",
            "merkle_path": ["hash1", "hash2"],
        }
    )
    client = Client(srv.url)
    mp = client.get_transaction_merkle_path("tx01")
    assert isinstance(mp, MerklePath)
    assert mp.block_id == "block01"
    assert mp.transaction_index == 3
    assert mp.merkle_root == "root01"
    assert mp.path == ["hash1", "hash2"]
    assert srv.capture.path == "/api/v2/transaction/tx01/merkle-path"
    client.close()


def test_get_transaction_output_raw(rest_server) -> None:
    """Transaction outputs pass through as raw JSON."""
    output = {
        "output": {"Transfer": {"destination": "mtc1abc", "amount": {"atoms": "100"}}},
        "spent_at_block_height": 42,
    }
    srv = rest_server(payload=output)
    client = Client(srv.url)
    assert client.get_transaction_output("tx01", 0) == output
    assert srv.capture.path == "/api/v2/transaction/tx01/output/0"
    client.close()


def test_submit_transaction(rest_server) -> None:
    """Submit POSTs the hex verbatim as text/plain and returns the tx id."""
    srv = rest_server(payload={"tx_id": "newtxid"})
    client = Client(srv.url)
    tx_id = client.submit_transaction("cafebabe")
    assert tx_id == "newtxid"
    assert srv.capture.method == "POST"
    assert srv.capture.path == "/api/v2/transaction"
    assert srv.capture.raw_body == b"cafebabe"
    assert srv.capture.headers.get("content-type", "").startswith("text/plain")
    client.close()


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"nope": 1}, id="missing-tx-id"),
        pytest.param("astring", id="bare-string"),
    ],
)
def test_submit_transaction_malformed_payload_raises_indexer_error(
    rest_server, payload: object
) -> None:
    """A response without a tx_id is a codec failure, not KeyError/TypeError."""
    srv = rest_server(payload=payload)
    client = Client(srv.url)
    try:
        with pytest.raises(IndexerError):
            client.submit_transaction("cafebabe")
    finally:
        client.close()
