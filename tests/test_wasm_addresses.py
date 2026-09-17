"""Tests for WASM address encoding (mirrors go-sdk/wasm/addresses.go)."""

from __future__ import annotations

import pytest
from wasm_helpers import derive

from mintlayer.wasm import Client, Network, WasmError


def test_pubkey_to_pubkeyhash_address(wasm: Client) -> None:
    _acct, _recv, pub, addr = derive(wasm)
    assert addr
    again = wasm.pubkey_to_pubkeyhash_address(pub, Network.MAINNET)
    assert addr == again  # deterministic
    assert addr.startswith("mtc1"), f"unexpected mainnet address prefix: {addr}"


def test_address_depends_on_network(wasm: Client) -> None:
    _acct, _recv, pub, mainnet = derive(wasm)
    testnet = wasm.pubkey_to_pubkeyhash_address(pub, Network.TESTNET)
    assert mainnet != testnet


def test_encode_destination(wasm: Client) -> None:
    _acct, _recv, _pub, addr = derive(wasm)
    dest = wasm.encode_destination(addr, Network.MAINNET)
    assert isinstance(dest, bytes) and len(dest) > 0
    assert dest == wasm.encode_destination(addr, Network.MAINNET)


def test_multisig_challenge_roundtrip(wasm: Client) -> None:
    pub1 = wasm.public_key_from_private_key(wasm.make_private_key())
    pub2 = wasm.public_key_from_private_key(wasm.make_private_key())
    challenge = wasm.encode_multisig_challenge(pub1 + pub2, 2, Network.MAINNET)
    assert isinstance(challenge, bytes) and len(challenge) > 0
    address = wasm.multisig_challenge_to_address(challenge, Network.MAINNET)
    assert address.startswith("mmtc1"), f"unexpected multisig address prefix: {address}"
    assert address == wasm.multisig_challenge_to_address(challenge, Network.MAINNET)


def test_multisig_address_differs_from_single_key_address(wasm: Client) -> None:
    pub1 = wasm.public_key_from_private_key(wasm.make_private_key())
    pub2 = wasm.public_key_from_private_key(wasm.make_private_key())
    multisig = wasm.multisig_challenge_to_address(
        wasm.encode_multisig_challenge(pub1 + pub2, 2, Network.MAINNET), Network.MAINNET
    )
    single = wasm.pubkey_to_pubkeyhash_address(pub1, Network.MAINNET)
    assert multisig != single


def test_invalid_public_key_address_raises(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.pubkey_to_pubkeyhash_address(b"abc", Network.MAINNET)


def test_encode_destination_invalid_address_raises(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_destination("not-an-address", Network.MAINNET)


def test_multisig_challenge_invalid_pubkeys_raise(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_multisig_challenge(b"\x00" * 10, 1, Network.MAINNET)


def test_multisig_challenge_to_address_garbage_raises(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.multisig_challenge_to_address(b"\xff\xff", Network.MAINNET)
