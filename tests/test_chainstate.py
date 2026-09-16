"""Tests for the chainstate module methods.

Mirrors the "chainstate module" section of go-sdk/node/client_test.go, plus
the order-info tests covering the deliberate Go-bug fix (``nonce: null``).
"""

from __future__ import annotations

from typing import Any

import pytest

from mintlayer.node import (
    Amount,
    ChainstateInfo,
    Client,
    Currency,
    JSONRPCError,
    OrderInfo,
    Outpoint,
    OutpointSourceID,
    Timestamp,
    tx_source_content,
)


def test_chainstate_info(rpc_server) -> None:
    result = {
        "best_block_height": 123456,
        "best_block_id": "aabbccdd",
        "best_block_timestamp": {"timestamp": 1700000000},
        "median_time": {"timestamp": 1699999500},
        "is_initial_block_download": False,
    }
    srv = rpc_server(result=result)
    client = Client(srv.url)
    info = client.chainstate_info()
    assert isinstance(info, ChainstateInfo)
    assert info.best_block_height == 123456
    assert info.best_block_id == "aabbccdd"
    assert info.best_block_timestamp == Timestamp(timestamp=1700000000)
    assert info.median_time == Timestamp(timestamp=1699999500)
    assert info.is_initial_block_download is False
    assert srv.capture.method == "chainstate_info"
    client.close()


def test_best_block_id(rpc_server) -> None:
    srv = rpc_server(result="deadbeef01020304")
    client = Client(srv.url)
    assert client.best_block_id() == "deadbeef01020304"
    assert srv.capture.method == "chainstate_best_block_id"
    client.close()


def test_best_block_id_null_result_raises(rpc_server) -> None:
    """A JSON null result for a non-optional str method raises JSONRPCError.

    The null guard must raise a type error mentioning "expected string result"
    rather than silently returning the string "None".
    """
    srv = rpc_server(result=None)
    client = Client(srv.url)
    with pytest.raises(JSONRPCError, match="expected string result"):
        client.best_block_id()
    client.close()


def test_best_block_height(rpc_server) -> None:
    srv = rpc_server(result=999)
    client = Client(srv.url)
    assert client.best_block_height() == 999
    assert srv.capture.method == "chainstate_best_block_height"
    client.close()


def test_block_id_at_height_null(rpc_server) -> None:
    """A JSON null result maps to None (unknown height)."""
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.block_id_at_height(9999999) is None
    assert srv.capture.method == "chainstate_block_id_at_height"
    assert srv.capture.params == {"height": 9999999}
    client.close()


def test_stake_pool_balance(rpc_server) -> None:
    srv = rpc_server(result={"atoms": "100000000000"})
    client = Client(srv.url)
    balance = client.stake_pool_balance("mpool1abc")
    assert balance == Amount(atoms="100000000000")
    assert balance.atoms == "100000000000"
    assert srv.capture.method == "chainstate_stake_pool_balance"
    assert srv.capture.params == {"pool_address": "mpool1abc"}
    client.close()


def test_stake_pool_balance_not_found(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.stake_pool_balance("mpool1missing") is None
    client.close()


def test_get_utxo_serializes_outpoint(rpc_server) -> None:
    """The Outpoint serialises to the daemon's tagged-union wire shape."""
    tx_id = "beefcafe01"
    outpoint = Outpoint(
        source_id=OutpointSourceID(type="Transaction", content=tx_source_content(tx_id)),
        index=0,
    )
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.get_utxo(outpoint) is None  # not found -> None
    assert srv.capture.method == "chainstate_get_utxo"
    assert srv.capture.params == {
        "outpoint": {
            "source_id": {"type": "Transaction", "content": {"tx_id": tx_id}},
            "index": 0,
        }
    }
    client.close()


def _order_payload(nonce: Any) -> dict[str, Any]:
    return {
        "conclude_key": "tql1conclude",
        "initially_asked": {"Coin": {"amount": {"atoms": "100"}}},
        "initially_given": {"Token": {"token_id": "tok1", "amount": {"atoms": "200"}}},
        "ask_balance": {"atoms": "900"},
        "give_balance": {"atoms": "700"},
        "nonce": nonce,
        "is_frozen": False,
    }


def test_order_info_nonce_null(rpc_server) -> None:
    """The daemon sends ``nonce: null`` for active orders -> None (Go SDK bug fix)."""
    srv = rpc_server(result=_order_payload(nonce=None))
    client = Client(srv.url)
    info = client.order_info("ord1xyz")
    assert info is not None
    assert info.nonce is None
    assert info.conclude_key == "tql1conclude"
    assert info.ask_balance == Amount(atoms="900")
    assert info.give_balance == Amount(atoms="700")
    assert info.is_frozen is False
    # Tagged-union payloads pass through as raw decoded JSON.
    assert info.initially_asked == {"Coin": {"amount": {"atoms": "100"}}}
    assert info.initially_given == {"Token": {"token_id": "tok1", "amount": {"atoms": "200"}}}
    client.close()


def test_order_info_nonce_present(rpc_server) -> None:
    srv = rpc_server(result=_order_payload(nonce=7))
    client = Client(srv.url)
    info = client.order_info("ord1xyz")
    assert isinstance(info, OrderInfo)
    assert info.nonce == 7
    client.close()


def test_order_info_not_found(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.order_info("ord1missing") is None
    client.close()


def test_orders_info_by_currencies_none_filters(rpc_server) -> None:
    """Both filter keys are always sent, as JSON null, when filters are None."""
    srv = rpc_server(result={})
    client = Client(srv.url)
    assert client.orders_info_by_currencies(None, None) == {}
    assert srv.capture.method == "chainstate_orders_info_by_currencies"
    assert srv.capture.params == {"ask_currency": None, "give_currency": None}
    client.close()


def test_orders_info_by_currencies_with_filters(rpc_server) -> None:
    srv = rpc_server(result={"ord1": _order_payload(nonce=None)})
    client = Client(srv.url)
    orders = client.orders_info_by_currencies(Currency.coin(), Currency.token("tok1"))
    assert set(orders) == {"ord1"}
    assert isinstance(orders["ord1"], OrderInfo)
    assert orders["ord1"].nonce is None
    # Coin omits content; Token carries the token id.
    assert srv.capture.params == {
        "ask_currency": {"type": "Coin"},
        "give_currency": {"type": "Token", "content": "tok1"},
    }
    client.close()
