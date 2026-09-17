"""Tests for the pure-Python WASM types and the host JSON serialisation.

The JSON shapes are the serde wire shapes consumed by the Rust module and
must match go-sdk/wasm/types.go exactly (tagged enums, redundant balance
objects, nested additional-info maps).
"""

from __future__ import annotations

import json

import pytest

from mintlayer.wasm import (
    Amount,
    CurrencyAmountKind,
    FreezableToken,
    Network,
    OrderBalance,
    OrderInfo,
    PoolInfo,
    SignatureHashType,
    SimpleCurrencyAmount,
    SourceId,
    TokenUnfreezable,
    TotalSupply,
    TxAdditionalInfo,
    WasmError,
)
from mintlayer.wasm.host import _json_dumps
from mintlayer.wasm.types import OrderBalance as OrderBalanceReimported


def test_wasm_error_prefix_contract() -> None:
    err = WasmError("mintlayer: boom")
    assert isinstance(err, Exception)
    assert str(err).startswith("mintlayer: ")


def test_enum_discriminants() -> None:
    assert [int(n) for n in Network] == [0, 1, 2, 3]
    assert [int(s) for s in SignatureHashType] == [0, 1, 2, 3]
    assert int(SourceId.SOURCE_TRANSACTION) == 0
    assert int(SourceId.SOURCE_BLOCK_REWARD) == 1
    assert [int(t) for t in TotalSupply] == [0, 1, 2]
    assert int(FreezableToken.NO) == 0 and int(FreezableToken.YES) == 1
    assert int(TokenUnfreezable.NO) == 0 and int(TokenUnfreezable.YES) == 1
    assert int(CurrencyAmountKind.COINS) == 0
    assert int(CurrencyAmountKind.TOKENS) == 1


def test_amount() -> None:
    one_ml = Amount.from_atoms("100000000000")
    assert one_ml.atoms == "100000000000"
    assert str(one_ml) == "100000000000"
    assert Amount.zero().atoms == "0"
    assert one_ml.to_json_value() == {"atoms": "100000000000"}
    assert one_ml == Amount.from_atoms("100000000000")


def test_simple_currency_amount_coins_shape() -> None:
    coins = SimpleCurrencyAmount.coins("5")
    assert coins.kind == CurrencyAmountKind.COINS
    assert coins.token_id is None
    assert coins.to_json_value() == {"coins": {"atoms": "5"}}


def test_simple_currency_amount_tokens_shape() -> None:
    tokens = SimpleCurrencyAmount.tokens("7", "mmltk1abc")
    assert tokens.kind == CurrencyAmountKind.TOKENS
    assert tokens.to_json_value() == {"tokens": {"amount": {"atoms": "7"}, "token_id": "mmltk1abc"}}


def test_simple_currency_amount_tokens_without_token_id_rejected() -> None:
    """A TOKENS amount without a token_id cannot be constructed."""
    with pytest.raises(ValueError, match="token_id is required for TOKENS amounts"):
        SimpleCurrencyAmount(atoms="1", kind=CurrencyAmountKind.TOKENS)


def test_simple_currency_amount_coins_with_token_id_rejected() -> None:
    """A COINS amount must not carry a token_id."""
    with pytest.raises(ValueError, match="token_id must be None for COINS amounts"):
        SimpleCurrencyAmount(atoms="1", token_id="mmltk1abc")


def test_simple_currency_amount_valid_constructions_still_work() -> None:
    """The invariant only rejects the two contradictory combinations."""
    coins = SimpleCurrencyAmount(atoms="1")
    assert coins.kind == CurrencyAmountKind.COINS
    assert coins.token_id is None
    tokens = SimpleCurrencyAmount(atoms="1", kind=CurrencyAmountKind.TOKENS, token_id="mmltk1abc")
    assert tokens.to_json_value() == {"tokens": {"amount": {"atoms": "1"}, "token_id": "mmltk1abc"}}


def test_order_balance_redundant_shape() -> None:
    balance = OrderBalance("9", None)
    assert balance.to_json_value() == {
        "atoms": "9",
        "amount": {"atoms": "9"},
        "token_id": None,
    }
    with_token = OrderBalance("9", "mmltk1abc")
    assert with_token.to_json_value() == {
        "atoms": "9",
        "amount": {"atoms": "9"},
        "token_id": "mmltk1abc",
    }


def test_pool_info_shape() -> None:
    info = PoolInfo(staker_balance=Amount.from_atoms("42"))
    assert info.to_json_value() == {"staker_balance": {"atoms": "42"}}


def test_order_info_shape() -> None:
    info = OrderInfo(
        initially_asked=SimpleCurrencyAmount.coins("1"),
        initially_given=SimpleCurrencyAmount.tokens("2", "mmltk1abc"),
        ask_balance=OrderBalance("3", None),
        give_balance=OrderBalance("4", "mmltk1abc"),
    )
    assert info.to_json_value() == {
        "initially_asked": {"coins": {"atoms": "1"}},
        "initially_given": {"tokens": {"amount": {"atoms": "2"}, "token_id": "mmltk1abc"}},
        "ask_balance": {"atoms": "3", "amount": {"atoms": "3"}, "token_id": None},
        "give_balance": {"atoms": "4", "amount": {"atoms": "4"}, "token_id": "mmltk1abc"},
    }


def test_tx_additional_info_empty_defaults() -> None:
    info = TxAdditionalInfo()
    assert info.pool_info == {}
    assert info.order_info == {}
    assert info.to_json_value() == {"pool_info": {}, "order_info": {}}


def test_tx_additional_info_nested_shape() -> None:
    info = TxAdditionalInfo(
        pool_info={"mpool1x": PoolInfo(staker_balance=Amount.from_atoms("5"))},
        order_info={
            "mordr1y": OrderInfo(
                initially_asked=SimpleCurrencyAmount.coins("1"),
                initially_given=SimpleCurrencyAmount.coins("2"),
                ask_balance=OrderBalance("3", None),
                give_balance=OrderBalance("4", None),
            )
        },
    )
    value = info.to_json_value()
    assert set(value) == {"pool_info", "order_info"}
    assert value["pool_info"]["mpool1x"] == {"staker_balance": {"atoms": "5"}}
    assert value["order_info"]["mordr1y"]["ask_balance"]["atoms"] == "3"


def test_order_balance_reimport_is_same_class() -> None:
    assert OrderBalanceReimported is OrderBalance


def test_host_json_dumps_honours_to_json_value() -> None:
    assert _json_dumps(Amount.from_atoms("5")) == '{"atoms":"5"}'
    assert _json_dumps(TxAdditionalInfo()) == '{"pool_info":{},"order_info":{}}'
    # Nesting is handled inside to_json_value implementations, not by the helper.
    info = TxAdditionalInfo(pool_info={"p": PoolInfo(staker_balance=Amount.from_atoms("5"))})
    expected = '{"pool_info":{"p":{"staker_balance":{"atoms":"5"}}},"order_info":{}}'
    assert _json_dumps(info) == expected


def test_host_json_dumps_plain_values() -> None:
    assert _json_dumps([1, 2, 3]) == "[1,2,3]"
    assert _json_dumps("x") == '"x"'
    assert json.loads(_json_dumps({"a": [True, None]})) == {"a": [True, None]}
