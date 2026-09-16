"""Tests for the indexer token / NFT endpoints.

Mirrors the "Token / NFT (3g)" section of go-sdk/indexer/client_test.go,
plus wire-shape pins for the freeze-flag pointer semantics and the
string-encoded tx_global_index.
"""

from __future__ import annotations

from mintlayer.indexer import Client, NFTInfo, TokenInfo


def test_list_tokens(rest_server) -> None:
    srv = rest_server(payload=["mmltk1aaa", "mmltk1bbb"])
    client = Client(srv.url)
    assert client.list_tokens() == ["mmltk1aaa", "mmltk1bbb"]
    assert srv.capture.path == "/api/v2/token"
    assert srv.capture.query == ""  # zero PageOpts -> no params
    client.close()


def _token_payload(**overrides: object) -> dict:
    payload = {
        "authority": "mtc1abc",
        "is_locked": False,
        "circulating_supply": {"atoms": "1000000", "decimal": "0.001"},
        "token_ticker": "TKN",
        "metadata_uri": "https://example.com/token.json",
        "number_of_decimals": 8,
        "total_supply": None,
        "frozen": False,
        "is_token_freezable": True,
        "next_nonce": 2,
    }
    payload.update(overrides)
    return payload


def test_get_token_not_frozen(rest_server) -> None:
    """total_supply may be null; is_token_freezable present when not frozen."""
    srv = rest_server(payload=_token_payload())
    client = Client(srv.url)
    info = client.get_token("mmltk1abc")
    assert isinstance(info, TokenInfo)
    assert info.authority == "mtc1abc"
    assert info.token_ticker == "TKN"
    assert info.number_of_decimals == 8
    assert info.total_supply is None
    assert info.circulating_supply.atoms == "1000000"
    assert info.frozen is False
    assert info.is_token_freezable is True
    assert info.is_token_unfreezable is None
    assert info.next_nonce == 2
    assert srv.capture.path == "/api/v2/token/mmltk1abc"
    client.close()


def test_get_token_frozen_flags_are_exclusive(rest_server) -> None:
    """Frozen tokens carry is_token_unfreezable and no is_token_freezable."""
    payload = _token_payload(frozen=True, is_token_unfreezable=False)
    del payload["is_token_freezable"]  # absent on the wire when frozen
    srv = rest_server(payload=payload)
    client = Client(srv.url)
    info = client.get_token("mmltk1abc")
    assert info.frozen is True
    assert info.is_token_freezable is None
    assert info.is_token_unfreezable is False
    client.close()


def test_get_token_transactions_string_encoded_index(rest_server) -> None:
    """tx_global_index arrives as a string and parses to an int."""
    srv = rest_server(
        payload=[
            {"tx_global_index": "12345", "tx_id": "tx01"},
            {"tx_global_index": "12346", "tx_id": "tx02"},
        ]
    )
    client = Client(srv.url)
    txs = client.get_token_transactions("mmltk1abc")
    assert len(txs) == 2
    assert txs[0].tx_global_index == 12345
    assert txs[0].tx_id == "tx01"
    assert txs[1].tx_global_index == 12346
    assert srv.capture.path == "/api/v2/token/mmltk1abc/transactions"
    client.close()


def test_find_tokens_by_ticker(rest_server) -> None:
    srv = rest_server(payload=["mmltk1aaa"])
    client = Client(srv.url)
    assert client.find_tokens_by_ticker("TKN") == ["mmltk1aaa"]
    assert srv.capture.path == "/api/v2/token/ticker/TKN"
    client.close()


def test_get_nft(rest_server) -> None:
    """NFT metadata decodes with null creator / media_uri fields."""
    srv = rest_server(
        payload={
            "owner": "mtc1abc",
            "token_id": "mmltk1nft",
            "metadata": {
                "creator": None,
                "name": "My NFT",
                "description": "A test NFT",
                "ticker": "NFT",
                "icon_uri": None,
                "additional_metadata_uri": None,
                "media_uri": None,
                "media_hash": "mediahash01",
            },
        }
    )
    client = Client(srv.url)
    nft = client.get_nft("mmltk1nft")
    assert isinstance(nft, NFTInfo)
    assert nft.owner == "mtc1abc"
    assert nft.token_id == "mmltk1nft"
    assert nft.metadata.name == "My NFT"
    assert nft.metadata.ticker == "NFT"
    assert nft.metadata.creator is None
    assert nft.metadata.media_uri is None
    assert nft.metadata.media_hash == "mediahash01"
    assert srv.capture.path == "/api/v2/nft/mmltk1nft"
    client.close()
