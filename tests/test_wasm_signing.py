"""Tests for WASM signing: witnesses, message signatures and verification.

Mirrors go-sdk TestSignChallengeRoundtrip, TestSignMessageForSpendingRoundtrip
and TestEncodeWitnessNoSignature; the transaction-witness flow uses a real
signed UTXO input so the sighash path is genuinely exercised.
"""

from __future__ import annotations

import pytest
from wasm_helpers import Wallet, fake_input, witness_for

from mintlayer.wasm import (
    Amount,
    Client,
    Network,
    SignatureHashType,
    TxAdditionalInfo,
    WasmError,
)

ONE_ML = Amount.from_atoms("100000000000")


@pytest.fixture
def wallet(wasm: Client) -> Wallet:
    return Wallet(wasm)


@pytest.fixture
def self_transfer(wasm: Client, wallet: Wallet) -> tuple[bytes, bytes, bytes]:
    """(input, output, unsigned tx) sending 1 ML back to the wallet."""
    inp = fake_input(wasm)
    out = wasm.encode_output_transfer(ONE_ML, wallet.addr, Network.MAINNET)
    return inp, out, wasm.encode_transaction(inp, out, 0)


# ── challenge signatures ──────────────────────────────────────────────────────


def test_sign_challenge_roundtrip(wasm: Client) -> None:
    priv = wasm.make_private_key()
    pub = wasm.public_key_from_private_key(priv)
    addr = wasm.pubkey_to_pubkeyhash_address(pub, Network.MAINNET)
    message = b"hello mintlayer"
    sig = wasm.sign_challenge(priv, message)
    assert len(sig) > 0
    assert wasm.verify_challenge(addr, Network.MAINNET, sig, message) is True


def test_verify_challenge_rejects_wrong_message(wasm: Client) -> None:
    priv = wasm.make_private_key()
    addr = wasm.pubkey_to_pubkeyhash_address(
        wasm.public_key_from_private_key(priv), Network.MAINNET
    )
    sig = wasm.sign_challenge(priv, b"hello mintlayer")
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.verify_challenge(addr, Network.MAINNET, sig, b"other message")


def test_verify_challenge_rejects_tampered_signature(wasm: Client) -> None:
    priv = wasm.make_private_key()
    addr = wasm.pubkey_to_pubkeyhash_address(
        wasm.public_key_from_private_key(priv), Network.MAINNET
    )
    sig = bytearray(wasm.sign_challenge(priv, b"hello mintlayer"))
    sig[-1] ^= 0x01
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.verify_challenge(addr, Network.MAINNET, bytes(sig), b"hello mintlayer")


def test_verify_challenge_invalid_address_raises(wasm: Client) -> None:
    priv = wasm.make_private_key()
    sig = wasm.sign_challenge(priv, b"m")
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.verify_challenge("not an address", Network.MAINNET, sig, b"m")


# ── spending signatures ───────────────────────────────────────────────────────


def test_sign_message_for_spending_roundtrip(wasm: Client) -> None:
    priv = wasm.make_private_key()
    pub = wasm.public_key_from_private_key(priv)
    message = b"spending message test"
    sig = wasm.sign_message_for_spending(priv, message)
    assert len(sig) > 0
    assert wasm.verify_signature_for_spending(pub, sig, message) is True


def test_verify_signature_for_spending_wrong_message_is_false(wasm: Client) -> None:
    priv = wasm.make_private_key()
    pub = wasm.public_key_from_private_key(priv)
    sig = wasm.sign_message_for_spending(priv, b"m")
    assert wasm.verify_signature_for_spending(pub, sig, b"other") is False


# ── transaction witnesses ─────────────────────────────────────────────────────


def test_encode_witness(wasm: Client, wallet: Wallet, self_transfer) -> None:
    inp, out, tx = self_transfer
    witness = witness_for(wasm, wallet, inp, out, tx)
    assert isinstance(witness, bytes) and len(witness) > 0


def test_encode_witness_no_signature(wasm: Client) -> None:
    witness = wasm.encode_witness_no_signature()
    assert isinstance(witness, bytes) and len(witness) > 0


def test_encode_witness_key_destination_mismatch_raises(
    wasm: Client, wallet: Wallet, self_transfer
) -> None:
    _inp, out, tx = self_transfer
    other = wasm.make_private_key()  # not the key behind wallet.addr
    with pytest.raises(WasmError, match="hash mismatch"):
        wasm.encode_witness(
            SignatureHashType.SIGHASH_ALL,
            other,
            wallet.addr,
            tx,
            b"\x01" + out,
            0,
            TxAdditionalInfo(),
            100,
            Network.MAINNET,
        )


def test_encode_witness_invalid_key_raises(wasm: Client, wallet: Wallet, self_transfer) -> None:
    _inp, out, tx = self_transfer
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_witness(
            SignatureHashType.SIGHASH_ALL,
            b"abc",
            wallet.addr,
            tx,
            b"\x01" + out,
            0,
            TxAdditionalInfo(),
            100,
            Network.MAINNET,
        )


# ── HTLC witness variants ─────────────────────────────────────────────────────


def test_encode_witness_htlc_spend_invalid_key_raises(
    wasm: Client, wallet: Wallet, self_transfer
) -> None:
    _inp, out, tx = self_transfer
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_witness_htlc_spend(
            SignatureHashType.SIGHASH_ALL,
            b"abc",
            wallet.addr,
            tx,
            b"\x01" + out,
            0,
            b"\x01" * 32,
            TxAdditionalInfo(),
            100,
            Network.MAINNET,
        )


def test_encode_witness_htlc_refund_single_sig_invalid_key_raises(
    wasm: Client, wallet: Wallet, self_transfer
) -> None:
    _inp, out, tx = self_transfer
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_witness_htlc_refund_single_sig(
            SignatureHashType.SIGHASH_ALL,
            b"abc",
            wallet.addr,
            tx,
            b"\x01" + out,
            0,
            TxAdditionalInfo(),
            100,
            Network.MAINNET,
        )


def test_encode_witness_htlc_refund_multisig_invalid_key_raises(
    wasm: Client, wallet: Wallet, self_transfer
) -> None:
    _inp, out, tx = self_transfer
    challenge = wasm.encode_multisig_challenge(wallet.pub + wallet.pub, 2, Network.MAINNET)
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_witness_htlc_refund_multisig(
            SignatureHashType.SIGHASH_ALL,
            b"abc",
            0,
            b"",
            challenge,
            tx,
            b"\x01" + out,
            0,
            TxAdditionalInfo(),
            100,
            Network.MAINNET,
        )
