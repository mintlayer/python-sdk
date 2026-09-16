"""Tests for the indexer address endpoints.

Mirrors the "Address (3e)" section of go-sdk/indexer/client_test.go. Note the
wire quirk: a UTXO's output payload lives under the key ``utxo``.
"""

from __future__ import annotations

from mintlayer.indexer import UTXO, AddressInfo, Client, DelegationInfo, TokenBalance


def test_get_address_info(rest_server) -> None:
    srv = rest_server(
        payload={
            "coin_balance": {"atoms": "100000000000", "decimal": "1.0"},
            "locked_coin_balance": {"atoms": "0", "decimal": "0"},
            "transaction_history": ["tx1", "tx2"],
            "tokens": [
                {
                    "token_id": "mmltk1tok",
                    "amount": {"atoms": "700", "decimal": "0.0000007"},
                }
            ],
        }
    )
    client = Client(srv.url)
    info = client.get_address_info("mtc1abc")
    assert isinstance(info, AddressInfo)
    assert info.coin_balance.atoms == "100000000000"
    assert info.coin_balance.decimal == "1.0"
    assert info.locked_coin_balance.atoms == "0"
    assert len(info.transaction_history) == 2
    assert isinstance(info.tokens[0], TokenBalance)
    assert info.tokens[0].token_id == "mmltk1tok"
    assert info.tokens[0].amount.atoms == "700"
    assert srv.capture.path == "/api/v2/address/mtc1abc"
    client.close()


def _utxo(source_id: str, index: int) -> dict:
    return {
        "outpoint": {"source_id": source_id, "index": index},
        "utxo": {"Transfer": {"destination": "mtc1abc", "amount": {"atoms": "100"}}},
    }


def test_get_spendable_utxos(rest_server) -> None:
    """UTXOs decode with the output payload taken from the wire key ``utxo``."""
    srv = rest_server(payload=[_utxo("tx1", 0), _utxo("tx2", 1)])
    client = Client(srv.url)
    utxos = client.get_spendable_utxos("mtc1abc")
    assert len(utxos) == 2
    assert all(isinstance(u, UTXO) for u in utxos)
    assert utxos[0].outpoint.source_id == "tx1"
    assert utxos[0].outpoint.index == 0
    assert utxos[1].outpoint.source_id == "tx2"
    assert utxos[1].outpoint.index == 1
    assert utxos[0].output == {"Transfer": {"destination": "mtc1abc", "amount": {"atoms": "100"}}}
    assert srv.capture.path == "/api/v2/address/mtc1abc/spendable-utxos"
    client.close()


def test_get_all_utxos(rest_server) -> None:
    srv = rest_server(payload=[_utxo("tx1", 0)])
    client = Client(srv.url)
    utxos = client.get_all_utxos("mtc1abc")
    assert len(utxos) == 1
    assert utxos[0].outpoint.source_id == "tx1"
    assert srv.capture.path == "/api/v2/address/mtc1abc/all-utxos"
    client.close()


def test_get_delegations(rest_server) -> None:
    srv = rest_server(
        payload=[
            {
                "delegation_id": "mdelg1abc",
                "pool_id": "mpool1xyz",
                "next_nonce": 3,
                "spend_destination": "mtc1dest",
                "balance": {"atoms": "500000000000", "decimal": "5.0"},
            }
        ]
    )
    client = Client(srv.url)
    delegations = client.get_delegations("mtc1abc")
    assert len(delegations) == 1
    assert isinstance(delegations[0], DelegationInfo)
    assert delegations[0].delegation_id == "mdelg1abc"
    assert delegations[0].pool_id == "mpool1xyz"
    assert delegations[0].next_nonce == 3
    assert delegations[0].balance.atoms == "500000000000"
    assert srv.capture.path == "/api/v2/address/mtc1abc/delegations"
    client.close()


def test_get_token_authority(rest_server) -> None:
    srv = rest_server(payload=["mmltk1aaa", "mmltk1bbb"])
    client = Client(srv.url)
    token_ids = client.get_token_authority("mtc1abc")
    assert len(token_ids) == 2
    assert token_ids[0] == "mmltk1aaa"
    assert srv.capture.path == "/api/v2/address/mtc1abc/token-authority"
    client.close()
