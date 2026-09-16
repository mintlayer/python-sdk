"""Tests for the indexer pool endpoints.

Mirrors the "Pool (3f)" section of go-sdk/indexer/client_test.go, including
the margin-ratio lenient forms ("3.5%", "10%", bare numbers) and the block
stats query-parameter pin.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from mintlayer.indexer import Client, Pool, PoolDelegation, PoolListOpts


def _pool_payload(**margin_overrides: object) -> dict:
    payload = {
        "pool_id": "mpool1abc",
        "decommission_destination": "mtc1dest",
        "staker_balance": {"atoms": "40000000000000", "decimal": "400000.0"},
        "margin_ratio_per_thousand": 100,
        "cost_per_block": {"atoms": "1000000000", "decimal": "10.0"},
        "vrf_public_key": "vrf01",
        "delegations_balance": {"atoms": "500000000000", "decimal": "5.0"},
    }
    payload.update(margin_overrides)
    return payload


def test_list_pools(rest_server) -> None:
    srv = rest_server(payload=[_pool_payload()])
    client = Client(srv.url)
    pools = client.list_pools(PoolListOpts())
    assert len(pools) == 1
    assert isinstance(pools[0], Pool)
    assert pools[0].pool_id == "mpool1abc"
    assert pools[0].staker_balance.atoms == "40000000000000"
    assert pools[0].margin_ratio_per_thousand == 100.0
    assert isinstance(pools[0].margin_ratio_per_thousand, float)
    assert srv.capture.path == "/api/v2/pool"
    client.close()


def test_list_pools_sort_param(rest_server) -> None:
    """sort=by_pledge and items=20 are sent; zero offset is omitted."""
    srv = rest_server(payload=[])
    client = Client(srv.url)
    assert client.list_pools(PoolListOpts(sort="by_pledge", offset=0, items=20)) == []
    assert "sort=by_pledge" in srv.capture.query
    assert "items=20" in srv.capture.query
    assert "offset" not in srv.capture.query
    client.close()


def test_get_pool(rest_server) -> None:
    srv = rest_server(payload=_pool_payload())
    client = Client(srv.url)
    pool = client.get_pool("mpool1abc")
    assert pool.pool_id == "mpool1abc"
    assert pool.decommission_destination == "mtc1dest"
    assert pool.cost_per_block.atoms == "1000000000"
    assert pool.delegations_balance.decimal == "5.0"
    assert srv.capture.path == "/api/v2/pool/mpool1abc"
    client.close()


@pytest.mark.parametrize(
    ("margin_value", "expected"),
    [
        pytest.param("3.5%", 3.5, id="float-percent"),
        pytest.param("10%", 10.0, id="integer-percent"),
        pytest.param(35, 35.0, id="bare-number"),
        pytest.param("10", 10.0, id="string-form"),
    ],
)
def test_get_pool_margin_ratio_lenient_forms(
    rest_server, margin_value: str | int, expected: float
) -> None:
    """The margin ratio accepts bare numbers, strings, and trailing %."""
    srv = rest_server(payload=_pool_payload(margin_ratio_per_thousand=margin_value))
    client = Client(srv.url)
    pool = client.get_pool("mpool1abc")
    assert pool.margin_ratio_per_thousand == expected
    assert isinstance(pool.margin_ratio_per_thousand, float)
    client.close()


def test_list_pools_margin_ratio_float_percent_wire(rest_server) -> None:
    """Go-parity check: percent-encoded margins decode through list_pools."""
    srv = rest_server(raw=json.dumps([_pool_payload(margin_ratio_per_thousand="3.5%")]))
    client = Client(srv.url)
    pools = client.list_pools(PoolListOpts())
    assert pools[0].margin_ratio_per_thousand == 3.5
    client.close()


_FROM = datetime.fromtimestamp(1700000000, tz=timezone.utc)
_TO = datetime.fromtimestamp(1700086400, tz=timezone.utc)


def test_get_pool_block_stats(rest_server) -> None:
    srv = rest_server(payload={"block_count": 42})
    client = Client(srv.url)
    assert client.get_pool_block_stats("mpool1abc", _FROM, _TO) == 42
    assert srv.capture.path == "/api/v2/pool/mpool1abc/block-stats"
    client.close()


def test_get_pool_block_stats_query_params(rest_server) -> None:
    """from/to unix seconds are always sent."""
    srv = rest_server(payload={"block_count": 0})
    client = Client(srv.url)
    client.get_pool_block_stats("mpool1abc", _FROM, _TO)
    assert "from=1700000000" in srv.capture.query
    assert "to=1700086400" in srv.capture.query
    client.close()


def test_get_pool_delegations(rest_server) -> None:
    srv = rest_server(
        payload=[
            {
                "delegation_id": "mdelg1abc",
                "next_nonce": 5,
                "spend_destination": "mtc1dest",
                "balance": {"atoms": "500000000000", "decimal": "5.0"},
                "creation_block_height": 10000,
            }
        ]
    )
    client = Client(srv.url)
    delegations = client.get_pool_delegations("mpool1abc")
    assert len(delegations) == 1
    assert isinstance(delegations[0], PoolDelegation)
    assert delegations[0].delegation_id == "mdelg1abc"
    assert delegations[0].next_nonce == 5
    assert delegations[0].creation_block_height == 10000
    assert srv.capture.path == "/api/v2/pool/mpool1abc/delegations"
    client.close()
