"""Tests for WASM transaction intents (mirrors go-sdk/wasm/intent.go).

Flow: derive the canonical message to sign, sign it with the input key,
encode the signed intent, then verify — including destination-mismatch
rejection.
"""

from __future__ import annotations

import pytest
from wasm_helpers import Wallet, fake_input

from mintlayer.wasm import Amount, Client, Network, WasmError


@pytest.fixture
def wallet(wasm: Client) -> Wallet:
    return Wallet(wasm)


@pytest.fixture
def tx_id(wasm: Client, wallet: Wallet) -> str:
    inp = fake_input(wasm)
    out = wasm.encode_output_transfer(
        Amount.from_atoms("100000000000"), wallet.addr, Network.MAINNET
    )
    tx = wasm.encode_transaction(inp, out, 0)
    return wasm.get_transaction_id(tx, True)


def test_message_to_sign_is_deterministic(wasm: Client, tx_id: str) -> None:
    message = wasm.make_transaction_intent_message_to_sign("test-intent", tx_id)
    assert isinstance(message, bytes) and len(message) > 0
    assert message == wasm.make_transaction_intent_message_to_sign("test-intent", tx_id)


def test_message_to_sign_depends_on_inputs(wasm: Client, tx_id: str) -> None:
    base = wasm.make_transaction_intent_message_to_sign("test-intent", tx_id)
    other_intent = wasm.make_transaction_intent_message_to_sign("other-intent", tx_id)
    other_txid = wasm.make_transaction_intent_message_to_sign("test-intent", "ff" * 32)
    assert base != other_intent
    assert base != other_txid


def test_intent_roundtrip(wasm: Client, wallet: Wallet, tx_id: str) -> None:
    message = wasm.make_transaction_intent_message_to_sign("test-intent", tx_id)
    signature = wasm.sign_challenge(wallet.recv, message)
    encoded = wasm.encode_signed_transaction_intent(message, [signature])
    assert isinstance(encoded, bytes) and len(encoded) > 0
    wasm.verify_transaction_intent(message, encoded, [wallet.addr], Network.MAINNET)


def test_intent_rejects_mismatched_destinations(wasm: Client, wallet: Wallet, tx_id: str) -> None:
    message = wasm.make_transaction_intent_message_to_sign("test-intent", tx_id)
    signature = wasm.sign_challenge(wallet.recv, message)
    encoded = wasm.encode_signed_transaction_intent(message, [signature])
    with pytest.raises(WasmError, match="^mintlayer: "):
        # Two destinations for a one-signature intent: must not verify.
        wasm.verify_transaction_intent(
            message, encoded, [wallet.addr, wallet.addr], Network.MAINNET
        )


def test_intent_rejects_wrong_message(wasm: Client, wallet: Wallet, tx_id: str) -> None:
    message = wasm.make_transaction_intent_message_to_sign("test-intent", tx_id)
    signature = wasm.sign_challenge(wallet.recv, message)
    encoded = wasm.encode_signed_transaction_intent(message, [signature])
    other = wasm.make_transaction_intent_message_to_sign("test-intent", "ff" * 32)
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.verify_transaction_intent(other, encoded, [wallet.addr], Network.MAINNET)


def test_intent_message_bad_txid_raises(wasm: Client) -> None:
    with pytest.raises(WasmError, match="Error parsing transaction id"):
        wasm.make_transaction_intent_message_to_sign("test-intent", "nothex")
