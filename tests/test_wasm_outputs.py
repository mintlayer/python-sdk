"""Tests for WASM output encoding (mirrors go-sdk/wasm/outputs.go).

Every ``encode_output_*`` method must return non-empty deterministic bytes;
error paths pin the ``mintlayer: `` prefix contract.
"""

from __future__ import annotations

import pytest
from wasm_helpers import HEIGHT, VRF_MAINNET, Wallet, fake_input

from mintlayer.wasm import (
    Amount,
    Client,
    FreezableToken,
    Network,
    TotalSupply,
    WasmError,
)

ONE_ML = Amount.from_atoms("100000000000")


@pytest.fixture
def wallet(wasm: Client) -> Wallet:
    return Wallet(wasm)


@pytest.fixture
def pool_id(wasm: Client) -> str:
    return wasm.get_pool_id(fake_input(wasm), Network.MAINNET)


@pytest.fixture
def token_id(wasm: Client) -> str:
    return wasm.get_token_id(fake_input(wasm), HEIGHT, Network.MAINNET)


@pytest.fixture
def delegation_id(wasm: Client) -> str:
    return wasm.get_delegation_id(fake_input(wasm), Network.MAINNET)


@pytest.fixture
def lock(wasm: Client) -> bytes:
    return wasm.encode_lock_for_block_count(100)


# ── transfers ─────────────────────────────────────────────────────────────────


def test_encode_output_transfer(wallet: Wallet, wasm: Client) -> None:
    out = wasm.encode_output_transfer(ONE_ML, wallet.addr, Network.MAINNET)
    assert isinstance(out, bytes) and len(out) > 0
    assert out == wasm.encode_output_transfer(ONE_ML, wallet.addr, Network.MAINNET)


def test_encode_output_token_transfer(wallet: Wallet, token_id: str, wasm: Client) -> None:
    out = wasm.encode_output_token_transfer(
        Amount.from_atoms("5"), wallet.addr, token_id, Network.MAINNET
    )
    assert len(out) > 0
    assert out != wasm.encode_output_transfer(Amount.from_atoms("5"), wallet.addr, Network.MAINNET)


def test_encode_output_lock_then_transfer(wallet: Wallet, lock: bytes, wasm: Client) -> None:
    out = wasm.encode_output_lock_then_transfer(ONE_ML, wallet.addr, lock, Network.MAINNET)
    assert len(out) > 0
    assert out != wasm.encode_output_transfer(ONE_ML, wallet.addr, Network.MAINNET)


def test_encode_output_token_lock_then_transfer(
    wallet: Wallet, token_id: str, lock: bytes, wasm: Client
) -> None:
    out = wasm.encode_output_token_lock_then_transfer(
        Amount.from_atoms("5"), wallet.addr, token_id, lock, Network.MAINNET
    )
    assert len(out) > 0


# ── burns and data ────────────────────────────────────────────────────────────


def test_encode_output_coin_burn(wasm: Client) -> None:
    out = wasm.encode_output_coin_burn(Amount.from_atoms("1"))
    assert len(out) > 0


def test_encode_output_token_burn(token_id: str, wasm: Client) -> None:
    out = wasm.encode_output_token_burn(Amount.from_atoms("1"), token_id, Network.MAINNET)
    assert len(out) > 0


def test_encode_output_data_deposit(wasm: Client) -> None:
    assert len(wasm.encode_output_data_deposit(b"hello on-chain")) > 0
    assert len(wasm.encode_output_data_deposit(b"")) > 0  # empty payload allowed


# ── staking outputs ───────────────────────────────────────────────────────────


def test_encode_output_create_delegation(wallet: Wallet, pool_id: str, wasm: Client) -> None:
    out = wasm.encode_output_create_delegation(pool_id, wallet.addr, Network.MAINNET)
    assert len(out) > 0


def test_encode_output_delegate_staking(delegation_id: str, wasm: Client) -> None:
    out = wasm.encode_output_delegate_staking(
        Amount.from_atoms("1000"), delegation_id, Network.MAINNET
    )
    assert len(out) > 0


def test_encode_output_create_stake_pool(wallet: Wallet, pool_id: str, wasm: Client) -> None:
    pool_data = wasm.encode_stake_pool_data(
        Amount.from_atoms("40000000000000"),
        wallet.addr,
        VRF_MAINNET,
        wallet.addr,
        100,
        Amount.from_atoms("100000000"),
        Network.MAINNET,
    )
    out = wasm.encode_output_create_stake_pool(pool_id, pool_data, Network.MAINNET)
    assert len(out) > 0


def test_encode_output_produce_block_from_stake(wallet: Wallet, pool_id: str, wasm: Client) -> None:
    out = wasm.encode_output_produce_block_from_stake(pool_id, wallet.addr, Network.MAINNET)
    assert len(out) > 0


# ── HTLC ──────────────────────────────────────────────────────────────────────


def test_encode_output_htlc_coin(wallet: Wallet, lock: bytes, wasm: Client) -> None:
    secret_hash = "03" * 20  # RIPEMD160(SHA256(secret)) as hex
    out = wasm.encode_output_htlc(
        ONE_ML, None, secret_hash, wallet.addr, wallet.addr, lock, Network.MAINNET
    )
    assert len(out) > 0


def test_encode_output_htlc_token(wallet: Wallet, token_id: str, lock: bytes, wasm: Client) -> None:
    out = wasm.encode_output_htlc(
        Amount.from_atoms("5"),
        token_id,
        "ab" * 20,
        wallet.addr,
        wallet.addr,
        lock,
        Network.MAINNET,
    )
    assert len(out) > 0


def test_encode_output_htlc_bad_secret_hash(wallet: Wallet, lock: bytes, wasm: Client) -> None:
    with pytest.raises(WasmError, match="htlc secret hash"):
        wasm.encode_output_htlc(
            ONE_ML, None, "03" * 32, wallet.addr, wallet.addr, lock, Network.MAINNET
        )


# ── issuance ──────────────────────────────────────────────────────────────────


def test_encode_output_issue_fungible_token_lockable(wallet: Wallet, wasm: Client) -> None:
    out = wasm.encode_output_issue_fungible_token(
        wallet.addr,
        "GLD",
        "https://example.com/gld.json",
        8,
        TotalSupply.LOCKABLE,
        None,
        FreezableToken.YES,
        HEIGHT,
        Network.MAINNET,
    )
    assert len(out) > 0


def test_encode_output_issue_fungible_token_fixed(wallet: Wallet, wasm: Client) -> None:
    out = wasm.encode_output_issue_fungible_token(
        wallet.addr,
        "GLD",
        "",
        8,
        TotalSupply.FIXED,
        Amount.from_atoms("1000000"),
        FreezableToken.NO,
        HEIGHT,
        Network.MAINNET,
    )
    assert len(out) > 0


def test_encode_output_issue_fungible_token_unlimited(wallet: Wallet, wasm: Client) -> None:
    """UNLIMITED supply must not carry a supply_amount (valid combination)."""
    out = wasm.encode_output_issue_fungible_token(
        wallet.addr,
        "GLD",
        "",
        8,
        TotalSupply.UNLIMITED,
        None,
        FreezableToken.NO,
        HEIGHT,
        Network.MAINNET,
    )
    assert isinstance(out, bytes) and len(out) > 0


def test_issue_fixed_supply_without_amount_raises(wallet: Wallet, wasm: Client) -> None:
    """FIXED without supply_amount is rejected before any WASM call."""
    with pytest.raises(ValueError, match="supply_amount is required for TotalSupply.FIXED"):
        wasm.encode_output_issue_fungible_token(
            wallet.addr,
            "GLD",
            "",
            8,
            TotalSupply.FIXED,
            None,
            FreezableToken.NO,
            HEIGHT,
            Network.MAINNET,
        )


def test_issue_non_fixed_supply_with_amount_raises(wallet: Wallet, wasm: Client) -> None:
    """A supply_amount together with a non-FIXED supply policy is rejected."""
    with pytest.raises(ValueError, match="must be None otherwise"):
        wasm.encode_output_issue_fungible_token(
            wallet.addr,
            "GLD",
            "",
            8,
            TotalSupply.UNLIMITED,
            Amount.from_atoms("1000000"),
            FreezableToken.NO,
            HEIGHT,
            Network.MAINNET,
        )


def test_issue_lockable_supply_with_amount_raises(wallet: Wallet, wasm: Client) -> None:
    """LOCKABLE behaves like UNLIMITED: a supply_amount is rejected."""
    with pytest.raises(ValueError, match="must be None otherwise"):
        wasm.encode_output_issue_fungible_token(
            wallet.addr,
            "GLD",
            "",
            8,
            TotalSupply.LOCKABLE,
            Amount.from_atoms("1000000"),
            FreezableToken.NO,
            HEIGHT,
            Network.MAINNET,
        )


def test_encode_output_issue_nft_minimal(wallet: Wallet, token_id: str, wasm: Client) -> None:
    out = wasm.encode_output_issue_nft(
        token_id,
        wallet.addr,
        "TestNFT",
        "TNFT",
        "TestNFTDescription",
        b"\x02" * 32,
        None,
        None,
        None,
        None,
        HEIGHT,
        Network.MAINNET,
    )
    assert len(out) > 0


def test_encode_output_issue_nft_full(wallet: Wallet, token_id: str, wasm: Client) -> None:
    out = wasm.encode_output_issue_nft(
        token_id,
        wallet.addr,
        "TestNFT",
        "TNFT",
        "TestNFTDescription",
        b"\x02" * 32,
        wallet.pub,
        "https://example.com/media",
        "https://example.com/icon",
        "https://example.com/meta",
        HEIGHT,
        Network.MAINNET,
    )
    assert len(out) > 0


# ── DEX orders ────────────────────────────────────────────────────────────────


def test_encode_create_order_output_coin_for_token(
    wallet: Wallet, token_id: str, wasm: Client
) -> None:
    out = wasm.encode_create_order_output(
        ONE_ML, None, Amount.from_atoms("20"), token_id, wallet.addr, Network.MAINNET
    )
    assert len(out) > 0


def test_encode_create_order_output_coin_for_coin(wallet: Wallet, wasm: Client) -> None:
    out = wasm.encode_create_order_output(
        ONE_ML, None, Amount.from_atoms("2"), None, wallet.addr, Network.MAINNET
    )
    assert len(out) > 0


# ── error contract ────────────────────────────────────────────────────────────


def test_output_error_messages_carry_mintlayer_prefix(wallet: Wallet, wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: Invalid atoms amount: xyz$"):
        wasm.encode_output_transfer(Amount.from_atoms("xyz"), wallet.addr, Network.MAINNET)
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_output_transfer(ONE_ML, "not-an-address", Network.MAINNET)
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_output_token_transfer(
            Amount.from_atoms("1"), wallet.addr, "bad-token", Network.MAINNET
        )
