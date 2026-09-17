"""Tests for WASM key derivation (mirrors go-sdk/wasm keys tests).

The derivation vectors use the standard "abandon ... about" mnemonic; the
private-path vs extended-public-path address equality is the key invariant
from Go's TestKeyDerivationChain.
"""

from __future__ import annotations

import pytest
from wasm_helpers import MNEMONIC, derive

from mintlayer.wasm import Client, Network, WasmError


def test_make_private_key(wasm: Client) -> None:
    key = wasm.make_private_key()
    assert len(key) > 0
    assert any(b != 0 for b in key), "private key is all zeros"


def test_make_private_key_is_random(wasm: Client) -> None:
    assert wasm.make_private_key() != wasm.make_private_key()


def test_make_default_account_privkey_is_deterministic(wasm: Client) -> None:
    key = wasm.make_default_account_privkey(MNEMONIC, Network.MAINNET)
    again = wasm.make_default_account_privkey(MNEMONIC, Network.MAINNET)
    assert key == again
    assert len(key) > 0


def test_public_key_from_private_key(wasm: Client) -> None:
    pub = wasm.public_key_from_private_key(wasm.make_private_key())
    assert len(pub) > 0
    assert any(b != 0 for b in pub)


def test_extended_key_pair_is_deterministic(wasm: Client) -> None:
    account = wasm.make_default_account_privkey(MNEMONIC, Network.MAINNET)
    ext1 = wasm.extended_public_key_from_extended_private_key(account)
    ext2 = wasm.extended_public_key_from_extended_private_key(account)
    assert ext1 == ext2
    assert len(ext1) > 0


def test_receiving_and_change_addresses_differ(wasm: Client) -> None:
    account = wasm.make_default_account_privkey(MNEMONIC, Network.MAINNET)
    recv0 = wasm.make_receiving_address(account, 0)
    recv1 = wasm.make_receiving_address(account, 1)
    change0 = wasm.make_change_address(account, 0)
    assert recv0 != recv1, "different key indices must derive different keys"
    assert recv0 != change0, "receiving and change chains must diverge"


def test_receiving_and_change_public_keys(wasm: Client) -> None:
    account = wasm.make_default_account_privkey(MNEMONIC, Network.MAINNET)
    ext_pub = wasm.extended_public_key_from_extended_private_key(account)
    recv_pub = wasm.make_receiving_address_public_key(ext_pub, 0)
    change_pub = wasm.make_change_address_public_key(ext_pub, 0)
    assert recv_pub == wasm.public_key_from_private_key(wasm.make_receiving_address(account, 0))
    assert change_pub == wasm.public_key_from_private_key(wasm.make_change_address(account, 0))


def test_full_derivation_chain_equality(wasm: Client) -> None:
    """Address derived via private keys equals the one via extended public keys."""
    account, _recv, pub, addr = derive(wasm)
    ext_pub = wasm.extended_public_key_from_extended_private_key(account)
    pub_from_ext = wasm.make_receiving_address_public_key(ext_pub, 0)
    addr_from_ext = wasm.pubkey_to_pubkeyhash_address(pub_from_ext, Network.MAINNET)
    assert pub == pub_from_ext
    assert addr == addr_from_ext
    assert addr


@pytest.mark.parametrize(
    ("label", "call"),
    [
        ("pub_from_garbage", lambda c: c.public_key_from_private_key(b"abc")),
        ("ext_from_garbage", lambda c: c.extended_public_key_from_extended_private_key(b"abc")),
        ("receiving_from_garbage", lambda c: c.make_receiving_address(b"abc", 0)),
        ("change_from_garbage", lambda c: c.make_change_address(b"abc", 0)),
        ("receiving_pub_from_garbage", lambda c: c.make_receiving_address_public_key(b"abc", 0)),
        ("change_pub_from_garbage", lambda c: c.make_change_address_public_key(b"abc", 0)),
        ("empty_mnemonic", lambda c: c.make_default_account_privkey("", Network.MAINNET)),
    ],
)
def test_key_error_paths(wasm: Client, label: str, call) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        call(wasm)
