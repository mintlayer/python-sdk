"""Tests for WASM object-ID derivation (mirrors go-sdk/wasm/ids.go).

Pool/token/delegation/order IDs are derived from the *encoded inputs* of the
issuance transaction; the tests use a real encoded UTXO input.
"""

from __future__ import annotations

import pytest
from wasm_helpers import HEIGHT, fake_input

from mintlayer.wasm import Client, Network, WasmError


def test_pool_id(wasm: Client) -> None:
    pool_id = wasm.get_pool_id(fake_input(wasm), Network.MAINNET)
    assert pool_id.startswith("mpool1")
    assert pool_id == wasm.get_pool_id(fake_input(wasm), Network.MAINNET)  # deterministic


def test_token_id(wasm: Client) -> None:
    token_id = wasm.get_token_id(fake_input(wasm), HEIGHT, Network.MAINNET)
    assert token_id.startswith("mmltk1")
    assert token_id == wasm.get_token_id(fake_input(wasm), HEIGHT, Network.MAINNET)


def test_delegation_id(wasm: Client) -> None:
    delegation_id = wasm.get_delegation_id(fake_input(wasm), Network.MAINNET)
    assert delegation_id.startswith("mdelg1")
    assert delegation_id == wasm.get_delegation_id(fake_input(wasm), Network.MAINNET)


def test_order_id(wasm: Client) -> None:
    order_id = wasm.get_order_id(fake_input(wasm), Network.MAINNET)
    assert order_id.startswith("mordr1")
    assert order_id == wasm.get_order_id(fake_input(wasm), Network.MAINNET)


def test_ids_are_distinct_per_object_kind(wasm: Client) -> None:
    inp = fake_input(wasm)
    ids = {
        wasm.get_pool_id(inp, Network.MAINNET),
        wasm.get_token_id(inp, HEIGHT, Network.MAINNET),
        wasm.get_delegation_id(inp, Network.MAINNET),
        wasm.get_order_id(inp, Network.MAINNET),
    }
    assert len(ids) == 4, "different object kinds must derive different ids"


def test_ids_differ_for_different_inputs(wasm: Client) -> None:
    a = wasm.get_pool_id(fake_input(wasm, txid=b"\x01" * 32), Network.MAINNET)
    b = wasm.get_pool_id(fake_input(wasm, txid=b"\x02" * 32), Network.MAINNET)
    assert a != b


def test_ids_depend_on_network(wasm: Client) -> None:
    inp = fake_input(wasm)
    assert wasm.get_pool_id(inp, Network.MAINNET) != wasm.get_pool_id(inp, Network.TESTNET)


def test_pool_id_garbage_inputs_raise(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.get_pool_id(b"\xff\xff", Network.MAINNET)


def test_pool_id_empty_inputs_raise(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.get_pool_id(b"", Network.MAINNET)


def test_delegation_id_garbage_inputs_raise(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.get_delegation_id(b"\xff\xff", Network.MAINNET)


def test_order_id_garbage_inputs_raise(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.get_order_id(b"\xff\xff", Network.MAINNET)


def test_token_id_garbage_inputs_raise(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.get_token_id(b"\xff\xff", HEIGHT, Network.MAINNET)
