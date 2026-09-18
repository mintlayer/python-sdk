"""Tests for the indexer block endpoints.

Mirrors the "Block (3c)" section of go-sdk/indexer/client_test.go, plus a
full Block/BlockHeader/BlockBody/Transaction decode pin.
"""

from __future__ import annotations

from mintlayer.indexer import Block, BlockHeader, Client, Transaction


def _block_payload() -> dict:
    return {
        "height": 5,
        "header": {
            "previous_block_id": "prevblock01",
            "timestamp": {"timestamp": 1700000000},
            "merkle_root": "merkleroot01",
            "witness_merkle_root": "witnessroot01",
            "consensus_data": {"PoS": {"vrf_output": "vrf01"}},
        },
        "body": {
            "reward": [{"Transfer": {"amount": {"atoms": "100"}}}],
            "transactions": [
                {
                    "id": "tx01",
                    "inputs": [],
                    "outputs": [],
                    "block_id": "block01",
                    "timestamp": "1700000000",
                    "confirmations": "3",
                }
            ],
        },
    }


def test_get_block_full_decode(rest_server) -> None:
    srv = rest_server(payload=_block_payload())
    client = Client(srv.url)
    block = client.get_block("aabbccdd")
    assert isinstance(block, Block)
    assert block.height == 5
    assert isinstance(block.header, BlockHeader)
    assert block.header.previous_block_id == "prevblock01"
    assert block.header.timestamp.timestamp == 1700000000
    assert block.header.merkle_root == "merkleroot01"
    assert block.header.witness_merkle_root == "witnessroot01"
    assert block.header.consensus_data == {"PoS": {"vrf_output": "vrf01"}}
    assert isinstance(block.body.transactions[0], Transaction)
    assert block.body.transactions[0].id == "tx01"
    assert block.body.transactions[0].confirmations == "3"
    assert srv.capture.path == "/api/v2/block/aabbccdd"
    client.close()


def test_get_block_header(rest_server) -> None:
    srv = rest_server(
        payload={
            "previous_block_id": "prevblock",
            "timestamp": {"timestamp": 1700000000},
            "merkle_root": "merkleroot",
            "witness_merkle_root": "witnessroot",
        }
    )
    client = Client(srv.url)
    header = client.get_block_header("blockid01")
    assert isinstance(header, BlockHeader)
    assert header.previous_block_id == "prevblock"
    assert header.merkle_root == "merkleroot"
    assert srv.capture.path == "/api/v2/block/blockid01/header"
    client.close()


def test_get_block_reward_raw_list(rest_server) -> None:
    """The reward is returned as raw JSON (no typed decode)."""
    reward = [{"Transfer": {"amount": {"atoms": "1000000000000"}}}]
    srv = rest_server(payload=reward)
    client = Client(srv.url)
    assert client.get_block_reward("aabbccdd") == reward
    assert srv.capture.path == "/api/v2/block/aabbccdd/reward"
    client.close()


def test_get_block_transaction_ids(rest_server) -> None:
    srv = rest_server(payload=["tx1", "tx2", "tx3"])
    client = Client(srv.url)
    ids = client.get_block_transaction_ids("aabbccdd")
    assert len(ids) == 3
    assert ids[0] == "tx1"
    assert srv.capture.path == "/api/v2/block/aabbccdd/transaction-ids"
    client.close()


def test_get_block_transaction_ids_null_result(rest_server) -> None:
    """A JSON null result maps to an empty list."""
    srv = rest_server(payload=None)
    client = Client(srv.url)
    assert client.get_block_transaction_ids("aabbccdd") == []
    client.close()
