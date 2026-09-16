"""Tests for the mempool module methods.

Mirrors the "mempool module" section of go-sdk/node/client_test.go.
"""

from __future__ import annotations

import pytest

from mintlayer.node import Amount, Client, FeeRate, FeeRatePoint, MempoolTx, TrustPolicy

_FEE_RATE_POINTS_WIRE = (
    '[[1024,{"amount_per_kb":{"atoms":"500"}}],[2048,{"amount_per_kb":{"atoms":"750"}}]]'
)


def test_contains_tx(rpc_server) -> None:
    srv = rpc_server(result=True)
    client = Client(srv.url)
    assert client.contains_tx("aabb1234") is True
    assert srv.capture.method == "mempool_contains_tx"
    assert srv.capture.params == {"tx_id": "aabb1234"}
    client.close()


def test_contains_orphan_tx(rpc_server) -> None:
    srv = rpc_server(result=False)
    client = Client(srv.url)
    assert client.contains_orphan_tx("aabb1234") is False
    assert srv.capture.method == "mempool_contains_orphan_tx"
    assert srv.capture.params == {"tx_id": "aabb1234"}
    client.close()


def test_get_transaction_found(rpc_server) -> None:
    srv = rpc_server(result={"id": "aabb1234", "status": "InMempool", "transaction": "cafebabe"})
    client = Client(srv.url)
    tx = client.get_transaction("aabb1234")
    assert tx == MempoolTx(id="aabb1234", status="InMempool", transaction="cafebabe")
    assert tx is not None
    assert tx.status == "InMempool"
    assert srv.capture.method == "mempool_get_transaction"
    assert srv.capture.params == {"tx_id": "aabb1234"}
    client.close()


def test_get_transaction_not_found(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.get_transaction("deadbeef") is None
    client.close()


def test_mempool_submit_transaction_untrusted(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.mempool_submit_transaction("cafebabe", TrustPolicy.UNTRUSTED) is None
    assert srv.capture.method == "mempool_submit_transaction"
    assert srv.capture.params == {
        "tx": "cafebabe",
        "options": {"trust_policy": "Untrusted"},
    }
    client.close()


def test_mempool_submit_transaction_trusted(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.mempool_submit_transaction("cafebabe", TrustPolicy.TRUSTED)
    assert srv.capture.params == {
        "tx": "cafebabe",
        "options": {"trust_policy": "Trusted"},
    }
    client.close()


def test_mempool_submit_transaction_accepts_plain_string(rpc_server) -> None:
    """A plain "Untrusted" string is normalised to the enum's wire value."""
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.mempool_submit_transaction("cafebabe", "Untrusted") is None
    assert srv.capture.method == "mempool_submit_transaction"
    assert srv.capture.params == {
        "tx": "cafebabe",
        "options": {"trust_policy": "Untrusted"},
    }
    client.close()


def test_mempool_submit_transaction_rejects_invalid_string(rpc_server) -> None:
    """An invalid policy string raises ValueError before any request is sent."""
    srv = rpc_server(result=None)
    client = Client(srv.url)
    with pytest.raises(ValueError):
        client.mempool_submit_transaction("cafebabe", "Bogus")
    assert srv.capture.request_count == 0
    client.close()


def test_get_fee_rate(rpc_server) -> None:
    srv = rpc_server(result={"amount_per_kb": {"atoms": "1000"}})
    client = Client(srv.url)
    rate = client.get_fee_rate(5)
    assert rate == FeeRate(amount_per_kb=Amount(atoms="1000"))
    assert rate is not None
    assert rate.amount_per_kb.atoms == "1000"
    assert srv.capture.method == "mempool_get_fee_rate"
    assert srv.capture.params == {"in_top_x_mb": 5}
    client.close()


def test_get_fee_rate_not_found(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.get_fee_rate(5) is None
    client.close()


def test_get_fee_rate_points(rpc_server) -> None:
    """Wire format: array of [size, feeRate] pairs (raw JSON result)."""
    srv = rpc_server(raw=_FEE_RATE_POINTS_WIRE)
    client = Client(srv.url)
    points = client.get_fee_rate_points()
    assert points == [
        FeeRatePoint(size=1024, rate=FeeRate(amount_per_kb=Amount(atoms="500"))),
        FeeRatePoint(size=2048, rate=FeeRate(amount_per_kb=Amount(atoms="750"))),
    ]
    assert points[0].size == 1024
    assert points[0].rate.amount_per_kb.atoms == "500"
    assert points[1].rate.amount_per_kb.atoms == "750"
    assert srv.capture.method == "mempool_get_fee_rate_points"
    client.close()


def test_memory_usage(rpc_server) -> None:
    srv = rpc_server(result=4096)
    client = Client(srv.url)
    assert client.memory_usage() == 4096
    assert srv.capture.method == "mempool_memory_usage"
    client.close()
