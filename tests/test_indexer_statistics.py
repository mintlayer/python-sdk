"""Tests for the indexer statistics endpoints.

Mirrors the "Statistics (3i)" section of go-sdk/indexer/client_test.go,
including the fee-rate query-parameter behaviour and bare-string decode.
"""

from __future__ import annotations

from mintlayer.indexer import Client, CoinStats

_COIN_STATS = {
    "circulating_supply": {"atoms": "1000000000000000", "decimal": "10000000.0"},
    "preminted": {"atoms": "400000000000000", "decimal": "4000000.0"},
    "burned": {"atoms": "0", "decimal": "0"},
    "staked": {"atoms": "500000000000000", "decimal": "5000000.0"},
}


def test_get_coin_statistics(rest_server) -> None:
    srv = rest_server(payload=_COIN_STATS)
    client = Client(srv.url)
    stats = client.get_coin_statistics()
    assert isinstance(stats, CoinStats)
    assert stats.circulating_supply.atoms == "1000000000000000"
    assert stats.preminted.decimal == "4000000.0"
    assert stats.burned.atoms == "0"
    assert stats.staked.decimal == "5000000.0"
    assert srv.capture.path == "/api/v2/statistics/coin"
    client.close()


def test_get_token_statistics(rest_server) -> None:
    srv = rest_server(payload=_COIN_STATS)
    client = Client(srv.url)
    stats = client.get_token_statistics("mmltk1abc")
    assert isinstance(stats, CoinStats)
    assert stats.circulating_supply.atoms == "1000000000000000"
    assert srv.capture.path == "/api/v2/statistics/token/mmltk1abc"
    client.close()


def test_get_token_statistics_percent_encodes_reserved_characters(rest_server) -> None:
    """A token id containing '/' or '?' must be percent-encoded in the path."""
    srv = rest_server(payload=_COIN_STATS)
    client = Client(srv.url)
    try:
        stats = client.get_token_statistics("tok/en?x")
        assert isinstance(stats, CoinStats)
        assert srv.capture.path == "/api/v2/statistics/token/tok%2Fen%3Fx"
        # Nothing may leak out of the path into the query string.
        assert srv.capture.query == ""
    finally:
        client.close()


def test_get_fee_rate_in_top_x_mb(rest_server) -> None:
    """in_top_x_mb=5 is sent and the bare JSON string result is returned."""
    srv = rest_server(payload="1000")
    client = Client(srv.url)
    rate = client.get_fee_rate(5)
    assert rate == "1000"
    assert isinstance(rate, str)
    assert "in_top_x_mb=5" in srv.capture.query
    assert srv.capture.path == "/api/v2/feerate"
    client.close()


def test_get_fee_rate_default_omits_param(rest_server) -> None:
    """The default call sends no in_top_x_mb param (server default 5 MB)."""
    srv = rest_server(payload="500")
    client = Client(srv.url)
    assert client.get_fee_rate() == "500"
    assert "in_top_x_mb" not in srv.capture.query
    assert srv.capture.query == ""
    client.close()
