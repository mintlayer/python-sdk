"""Tests for the indexer DEX order endpoints.

Mirrors the "Order (3h)" section of go-sdk/indexer/client_test.go, including
the string-encoded nonce forms.
"""

from __future__ import annotations

import json

from mintlayer.indexer import Client, Order, PageOpts


def _order_payload(**overrides: object) -> dict:
    payload = {
        "order_id": "mord1abc",
        "conclude_destination": "mtc1dest",
        "give_currency": {},
        "initially_given": {"atoms": "100000000000", "decimal": "1.0"},
        "give_balance": {"atoms": "90000000000", "decimal": "0.9"},
        "ask_currency": {},
        "initially_asked": {"atoms": "80000000000", "decimal": "0.8"},
        "ask_balance": {"atoms": "70000000000", "decimal": "0.7"},
        "nonce": 5,
    }
    payload.update(overrides)
    return payload


def test_list_orders(rest_server) -> None:
    """Orders decode, including a nonce serialised as a string."""
    srv = rest_server(raw=json.dumps([_order_payload(nonce="5")]))
    client = Client(srv.url)
    orders = client.list_orders(PageOpts())
    assert len(orders) == 1
    assert isinstance(orders[0], Order)
    assert orders[0].order_id == "mord1abc"
    assert orders[0].nonce == 5
    assert orders[0].initially_given.atoms == "100000000000"
    assert orders[0].give_balance.decimal == "0.9"
    assert orders[0].ask_balance.atoms == "70000000000"
    assert srv.capture.path == "/api/v2/order"
    assert srv.capture.query == ""
    client.close()


def test_get_order(rest_server) -> None:
    srv = rest_server(payload=_order_payload())
    client = Client(srv.url)
    order = client.get_order("mord1abc")
    assert isinstance(order, Order)
    assert order.order_id == "mord1abc"
    assert order.conclude_destination == "mtc1dest"
    assert order.nonce == 5
    assert srv.capture.path == "/api/v2/order/mord1abc"
    client.close()


def test_get_order_string_encoded_nonce(rest_server) -> None:
    srv = rest_server(raw=json.dumps(_order_payload(nonce="5")))
    client = Client(srv.url)
    assert client.get_order("mord1abc").nonce == 5
    client.close()


def test_list_orders_by_pair_path_and_query(rest_server) -> None:
    """The pair route is /order/pair/{ask}_{give} and forwards PageOpts."""
    srv = rest_server(payload=[])
    client = Client(srv.url)
    assert client.list_orders_by_pair("ML", "mmltk1abc", PageOpts(offset=10, items=20)) == []
    assert srv.capture.path == "/api/v2/order/pair/ML_mmltk1abc"
    assert "offset=10" in srv.capture.query
    assert "items=20" in srv.capture.query
    client.close()
