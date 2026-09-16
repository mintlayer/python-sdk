"""DEX order tests for the wallet client.

Mirrors go-sdk/wallet/orders_test.go: OutputValue wire shapes, the client-side
validation that never reaches the HTTP server, the order action params shapes,
and the CurrencyFilter encodings for list_all_active_orders.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from mintlayer.wallet import (
    Amount,
    Client,
    ConcludeOrderParams,
    CreateOrderParams,
    FillOrderParams,
    FreezeOrderParams,
    ListOrdersParams,
    OrderCreated,
    OutputValue,
    RPCError,
    coin_filter,
    token_filter,
)

_ZERO_OPTIONS = {"in_top_x_mb": None, "broadcast_to_mempool": None}


def _send_result(tx_id: str) -> dict:
    return {
        "tx_id": tx_id,
        "fees": {"coins": {"atoms": "10000", "decimal": "0.0001"}, "tokens": {}},
        "broadcasted": True,
    }


_OWN_ORDERS = [
    {
        "order_id": "ord1owned",
        "initially_asked": {
            "type": "Token",
            "content": {"id": "tok1askedabc", "amount": {"atoms": "100000000", "decimal": "1.0"}},
        },
        "initially_given": {
            "type": "Coin",
            "content": {"amount": {"atoms": "5000000000", "decimal": "50.0"}},
        },
        "existing_order_data": {
            "ask_balance": {"atoms": "90000000", "decimal": "0.9"},
            "give_balance": {"atoms": "4500000000", "decimal": "45.0"},
            "is_frozen": True,
            "creation_timestamp": {"timestamp": 1700000000},
        },
        "is_marked_as_frozen_in_wallet": True,
        "is_marked_as_concluded_in_wallet": False,
    },
    {
        "order_id": "ord2owned",
        "initially_asked": {"type": "Coin", "content": {"amount": {"atoms": "10"}}},
        "initially_given": {
            "type": "Token",
            "content": {"id": "tok2given", "amount": {"atoms": "20"}},
        },
        "existing_order_data": None,
        "is_marked_as_frozen_in_wallet": False,
        "is_marked_as_concluded_in_wallet": True,
    },
]

_ACTIVE_ORDERS = [
    {
        "order_id": "ord1active",
        "initially_asked": {"type": "Coin", "content": {"amount": {"atoms": "1000000000000"}}},
        "initially_given": {
            "type": "Token",
            "content": {"id": "tok1givenabc", "amount": {"atoms": "2500000000"}},
        },
        "ask_balance": {"atoms": "1000000000000"},
        "give_balance": {"atoms": "2500000000"},
        "is_own": True,
    }
]


# --- OutputValue wire encoding ------------------------------------------------


def test_output_value_coin_wire_shape() -> None:
    value = OutputValue.coins(atoms="1000000000000")
    assert value.to_json() == {"type": "Coin", "content": {"amount": {"atoms": "1000000000000"}}}
    # Coin values carry no token id key at all.
    assert "id" not in value.to_json()["content"]


def test_output_value_token_wire_shape() -> None:
    value = OutputValue.tokens("tok1abc", atoms="250000000")
    assert value.to_json() == {
        "type": "Token",
        "content": {"id": "tok1abc", "amount": {"atoms": "250000000"}},
    }


def test_output_value_token_without_id_raises() -> None:
    value = OutputValue.tokens("", atoms="2")
    with pytest.raises(ValueError, match="requires TokenID"):
        value.to_json()


def test_output_value_without_amount_raises() -> None:
    with pytest.raises(ValueError, match="requires an amount"):
        OutputValue.coins(atoms="").to_json()


def test_output_value_unknown_type_from_json_raises() -> None:
    with pytest.raises(ValueError, match="unknown OutputValue type"):
        OutputValue.from_json({"type": "NFT", "content": {"amount": {"atoms": "1"}}})


@pytest.mark.parametrize(
    "value",
    [
        OutputValue.coins(atoms="1000000000000", decimal="10000.0"),
        OutputValue.tokens("tok1roundtrip", atoms="999", decimal="0.000000999"),
    ],
    ids=["coin", "token"],
)
def test_output_value_round_trip(value: OutputValue) -> None:
    assert OutputValue.from_json(value.to_json()) == value


# --- CreateOrder ---------------------------------------------------------------


def test_create_order_wire_shape(rpc_server) -> None:
    srv = rpc_server(result={"order_id": "ord1created", "tx_id": "tx1created", "broadcasted": True})
    client = Client(srv.url)
    got = client.create_order(
        CreateOrderParams(
            account=0,
            ask=OutputValue.coins(atoms="1000000000000"),
            give=OutputValue.tokens("tok1giveabc", atoms="250000000"),
            conclude_address="tmltool1conclude",
        )
    )
    assert got == OrderCreated(order_id="ord1created", tx_id="tx1created", broadcasted=True)
    assert srv.capture.method == "order_create"
    assert srv.capture.params == {
        "account": 0,
        "ask": {"type": "Coin", "content": {"amount": {"atoms": "1000000000000"}}},
        "give": {
            "type": "Token",
            "content": {"id": "tok1giveabc", "amount": {"atoms": "250000000"}},
        },
        "conclude_address": "tmltool1conclude",
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_create_order_token_side_without_id_no_request(rpc_server) -> None:
    """A token side missing its TokenID fails before any HTTP request."""
    srv = rpc_server(result=None)
    client = Client(srv.url)
    params = CreateOrderParams(
        account=0,
        ask=OutputValue.coins(atoms="1"),
        give=OutputValue.tokens("", atoms="2"),
        conclude_address="tmltool1conclude",
    )
    with pytest.raises(ValueError, match="requires TokenID"):
        client.create_order(params)
    assert srv.capture.request_count == 0
    client.close()


def test_create_order_missing_amount_no_request(rpc_server) -> None:
    """An OutputValue with no amount fails before any HTTP request."""
    srv = rpc_server(result=None)
    client = Client(srv.url)
    params = CreateOrderParams(
        account=0,
        ask=OutputValue.coins(atoms=""),
        give=OutputValue.coins(atoms="2"),
        conclude_address="tmltool1conclude",
    )
    with pytest.raises(ValueError, match="requires an amount"):
        client.create_order(params)
    assert srv.capture.request_count == 0
    client.close()


# --- ConcludeOrder / FillOrder / FreezeOrder -----------------------------------


def test_conclude_order_output_address_null(rpc_server) -> None:
    srv = rpc_server(result=_send_result("tx1c2"))
    client = Client(srv.url)
    got = client.conclude_order(ConcludeOrderParams(account=0, order_id="ord1c2"))
    assert got.tx_id == "tx1c2"
    assert got.broadcasted is True
    assert srv.capture.method == "order_conclude"
    # The key stays on the wire with an explicit null (never omitted).
    assert srv.capture.params == {
        "account": 0,
        "order_id": "ord1c2",
        "output_address": None,
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_conclude_order_with_output_address(rpc_server) -> None:
    srv = rpc_server(result=_send_result("tx1conclude"))
    client = Client(srv.url)
    got = client.conclude_order(
        ConcludeOrderParams(account=0, order_id="ord1conclude", output_address="tmltool1remainder")
    )
    assert got.tx_id == "tx1conclude"
    assert srv.capture.params["output_address"] == "tmltool1remainder"
    client.close()


def test_fill_order_wire_shape(rpc_server) -> None:
    srv = rpc_server(result=_send_result("tx1fill"))
    client = Client(srv.url)
    got = client.fill_order(
        FillOrderParams(
            account=0,
            order_id="ord1fill",
            fill_amount_in_ask_currency=Amount(atoms="100000000", decimal="1.0"),
        )
    )
    assert got.tx_id == "tx1fill"
    assert srv.capture.method == "order_fill"
    # Key name "fill_amount_in_ask_currency" is pinned; output_address null.
    assert srv.capture.params == {
        "account": 0,
        "order_id": "ord1fill",
        "fill_amount_in_ask_currency": {"atoms": "100000000", "decimal": "1.0"},
        "output_address": None,
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_freeze_order_wire_shape(rpc_server) -> None:
    srv = rpc_server(result=_send_result("tx1freeze"))
    client = Client(srv.url)
    got = client.freeze_order(FreezeOrderParams(account=0, order_id="ord1freeze"))
    assert got.tx_id == "tx1freeze"
    assert srv.capture.method == "order_freeze"
    assert srv.capture.params == {
        "account": 0,
        "order_id": "ord1freeze",
        "options": _ZERO_OPTIONS,
    }
    client.close()


# --- Listings ------------------------------------------------------------------


def test_list_own_orders_decoding(rpc_server) -> None:
    srv = rpc_server(result=_OWN_ORDERS)
    client = Client(srv.url)
    got = client.list_own_orders(0)
    assert srv.capture.method == "order_list_own"
    assert srv.capture.params == {"account": 0}
    assert len(got) == 2

    first = got[0]
    assert first.order_id == "ord1owned"
    # initially_asked: Token carrying both atoms and decimal.
    assert first.initially_asked == OutputValue.tokens(
        "tok1askedabc", atoms="100000000", decimal="1.0"
    )
    # initially_given: Coin with no token id.
    assert first.initially_given == OutputValue.coins(atoms="5000000000", decimal="50.0")
    existing = first.existing_order_data
    assert existing is not None
    assert existing.ask_balance == Amount(atoms="90000000", decimal="0.9")
    assert existing.give_balance == Amount(atoms="4500000000", decimal="45.0")
    assert existing.is_frozen is True
    assert existing.creation_timestamp.timestamp == 1700000000
    assert first.is_marked_as_frozen_in_wallet is True
    assert first.is_marked_as_concluded_in_wallet is False

    second = got[1]
    assert second.order_id == "ord2owned"
    # A null existing_order_data decodes to None.
    assert second.existing_order_data is None
    assert second.is_marked_as_concluded_in_wallet is True
    client.close()


def test_list_own_orders_null_result_returns_empty(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.list_own_orders(0) == []
    client.close()


def test_list_all_active_orders_nil_filters(rpc_server) -> None:
    srv = rpc_server(result=[])
    client = Client(srv.url)
    got = client.list_all_active_orders(ListOrdersParams(account=3))
    assert got == []
    assert srv.capture.method == "order_list_all_active"
    # Nil filters are encoded as JSON null on both keys.
    assert srv.capture.params == {"account": 3, "ask_currency": None, "give_currency": None}
    client.close()


def test_list_all_active_orders_with_filters(rpc_server) -> None:
    srv = rpc_server(result=_ACTIVE_ORDERS)
    client = Client(srv.url)
    got = client.list_all_active_orders(
        ListOrdersParams(
            account=0,
            ask_currency=coin_filter(),
            give_currency=token_filter("tok1givenabc"),
        )
    )
    assert len(got) == 1
    order = got[0]
    assert order.order_id == "ord1active"
    assert order.initially_asked == OutputValue.coins(atoms="1000000000000")
    assert order.initially_given == OutputValue.tokens("tok1givenabc", atoms="2500000000")
    assert order.ask_balance == Amount(atoms="1000000000000")
    assert order.give_balance == Amount(atoms="2500000000")
    assert order.is_own is True
    # Coin filters carry no content; token filters carry the id as content.
    assert srv.capture.params == {
        "account": 0,
        "ask_currency": {"type": "Coin"},
        "give_currency": {"type": "Token", "content": "tok1givenabc"},
    }
    client.close()


def test_token_filter_empty_id_raises() -> None:
    with pytest.raises(ValueError, match="token id"):
        token_filter("")


# --- Error propagation ---------------------------------------------------------


@pytest.mark.parametrize(
    "invoke",
    [
        pytest.param(
            lambda c: c.create_order(
                CreateOrderParams(
                    account=0,
                    ask=OutputValue.coins(atoms="1"),
                    give=OutputValue.coins(atoms="2"),
                    conclude_address="tmltool1conclude",
                )
            ),
            id="create_order",
        ),
        pytest.param(
            lambda c: c.conclude_order(ConcludeOrderParams(account=0, order_id="ord1")),
            id="conclude_order",
        ),
        pytest.param(
            lambda c: c.fill_order(
                FillOrderParams(
                    account=0, order_id="ord1", fill_amount_in_ask_currency=Amount(atoms="1")
                )
            ),
            id="fill_order",
        ),
        pytest.param(
            lambda c: c.freeze_order(FreezeOrderParams(account=0, order_id="ord1")),
            id="freeze_order",
        ),
        pytest.param(lambda c: c.list_own_orders(0), id="list_own_orders"),
        pytest.param(
            lambda c: c.list_all_active_orders(ListOrdersParams(account=0)),
            id="list_all_active_orders",
        ),
    ],
)
def test_order_methods_rpc_error_propagates(rpc_server, invoke: Callable[[Client], object]) -> None:
    srv = rpc_server(error=(-32000, "order failure"))
    client = Client(srv.url)
    with pytest.raises(RPCError) as excinfo:
        invoke(client)
    assert excinfo.value.code == -32000
    assert excinfo.value.message == "order failure"
    client.close()
