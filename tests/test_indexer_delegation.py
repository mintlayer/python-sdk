"""Tests for the indexer delegation endpoint.

Mirrors the lenient-numeric raw-wire cases of go-sdk/indexer/client_test.go
(TestDelegation_NextNonce_StringForm): the server serialises several numeric
fields as strings.
"""

from __future__ import annotations

import json

from mintlayer.indexer import Client, Delegation


def _delegation_payload(**overrides: object) -> dict:
    payload = {
        "delegation_id": "mdelg1abc",
        "pool_id": "mpool1xyz",
        "next_nonce": 7,
        "spend_destination": "mtc1dest",
        "balance": {"atoms": "500000000000", "decimal": "5.0"},
        "creation_block_height": 10000,
    }
    payload.update(overrides)
    return payload


def test_get_delegation(rest_server) -> None:
    """Plain numeric wire values decode to ints."""
    srv = rest_server(payload=_delegation_payload())
    client = Client(srv.url)
    delegation = client.get_delegation("mdelg1abc")
    assert isinstance(delegation, Delegation)
    assert delegation.delegation_id == "mdelg1abc"
    assert delegation.pool_id == "mpool1xyz"
    assert delegation.next_nonce == 7
    assert delegation.spend_destination == "mtc1dest"
    assert delegation.balance.atoms == "500000000000"
    assert delegation.creation_block_height == 10000
    assert srv.capture.path == "/api/v2/delegation/mdelg1abc"
    client.close()


def test_get_delegation_string_encoded_numerics(rest_server) -> None:
    """``next_nonce``/``creation_block_height`` as strings parse to ints."""
    srv = rest_server(
        raw=json.dumps(_delegation_payload(next_nonce="7", creation_block_height="10000"))
    )
    client = Client(srv.url)
    delegation = client.get_delegation("mdelg1abc")
    assert delegation.next_nonce == 7
    assert delegation.creation_block_height == 10000
    assert isinstance(delegation.next_nonce, int)
    assert isinstance(delegation.creation_block_height, int)
    client.close()
