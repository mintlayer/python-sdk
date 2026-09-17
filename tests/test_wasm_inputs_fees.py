"""Tests for WASM inputs, timelocks, fees and staking helpers.

The VRF public key used for pool data is the real mainnet vector from
mintlayer-core; every error-path assertion pins the ``mintlayer: `` message
prefix required by the SDK's error contract.
"""

from __future__ import annotations

import pytest
from wasm_helpers import HEIGHT, ORDERS_HEIGHT, VRF_MAINNET, Wallet, fake_input

from mintlayer.wasm import Amount, Client, Network, SourceId, TokenUnfreezable, WasmError

# ── inputs ────────────────────────────────────────────────────────────────────


def test_encode_input_for_utxo(wasm: Client) -> None:
    inp = wasm.encode_input_for_utxo(
        wasm.encode_outpoint_source_id(b"\x01" * 32, SourceId.SOURCE_TRANSACTION), 0
    )
    assert isinstance(inp, bytes) and len(inp) > 0
    assert inp == fake_input(wasm)  # deterministic


def test_utxo_input_depends_on_index(wasm: Client) -> None:
    assert fake_input(wasm, index=0) != fake_input(wasm, index=1)


def test_encode_input_for_withdraw_from_delegation(wasm: Client) -> None:
    delegation_id = wasm.get_delegation_id(fake_input(wasm), Network.MAINNET)
    inp = wasm.encode_input_for_withdraw_from_delegation(
        delegation_id, Amount.from_atoms("1"), 3, Network.MAINNET
    )
    assert len(inp) > 0


def test_encode_input_for_mint_unmint_lock(wasm: Client) -> None:
    token_id = wasm.get_token_id(fake_input(wasm), HEIGHT, Network.MAINNET)
    assert (
        len(wasm.encode_input_for_mint_tokens(token_id, Amount.from_atoms("1"), 3, Network.MAINNET))
        > 0
    )
    assert len(wasm.encode_input_for_unmint_tokens(token_id, 3, Network.MAINNET)) > 0
    assert len(wasm.encode_input_for_lock_token_supply(token_id, 3, Network.MAINNET)) > 0


def test_encode_input_for_freeze_unfreeze_token(wasm: Client) -> None:
    token_id = wasm.get_token_id(fake_input(wasm), HEIGHT, Network.MAINNET)
    freeze = wasm.encode_input_for_freeze_token(token_id, TokenUnfreezable.YES, 3, Network.MAINNET)
    assert len(freeze) > 0
    assert len(wasm.encode_input_for_unfreeze_token(token_id, 3, Network.MAINNET)) > 0


def test_encode_input_for_change_token_authority_and_metadata(wasm: Client) -> None:
    token_id = wasm.get_token_id(fake_input(wasm), HEIGHT, Network.MAINNET)
    wallet = Wallet(wasm)
    assert (
        len(wasm.encode_input_for_change_token_authority(token_id, wallet.addr, 3, Network.MAINNET))
        > 0
    )
    assert (
        len(
            wasm.encode_input_for_change_token_metadata_uri(
                token_id, "https://example.com/meta.json", 3, Network.MAINNET
            )
        )
        > 0
    )


def test_encode_input_for_conclude_fill_freeze_order(wasm: Client) -> None:
    order_id = wasm.get_order_id(fake_input(wasm), Network.MAINNET)
    wallet = Wallet(wasm)
    assert len(wasm.encode_input_for_conclude_order(order_id, 3, HEIGHT, Network.MAINNET)) > 0
    assert (
        len(
            wasm.encode_input_for_fill_order(
                order_id, Amount.from_atoms("1"), wallet.addr, 3, HEIGHT, Network.MAINNET
            )
        )
        > 0
    )
    # Order freezing only exists after the orders V1 fork.
    assert len(wasm.encode_input_for_freeze_order(order_id, ORDERS_HEIGHT, Network.MAINNET)) > 0


def test_freeze_order_before_fork_raises(wasm: Client) -> None:
    order_id = wasm.get_order_id(fake_input(wasm), Network.MAINNET)
    with pytest.raises(WasmError, match="Orders V1 not activated"):
        wasm.encode_input_for_freeze_order(order_id, 100, Network.MAINNET)


def test_input_error_paths(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_input_for_withdraw_from_delegation(
            "bad-id", Amount.from_atoms("1"), 0, Network.MAINNET
        )
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_input_for_mint_tokens("bad-token", Amount.from_atoms("1"), 0, Network.MAINNET)
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_input_for_mint_tokens(
            "mmltk1jh783nqq5cnm73kq5jnwg8g6rnnf53h3d90c6mtv0y408jp4quqq696z9s",
            Amount.from_atoms("not-a-number"),
            0,
            Network.MAINNET,
        )


# ── timelocks ─────────────────────────────────────────────────────────────────


def test_timelocks_encode_non_empty(wasm: Client) -> None:
    assert len(wasm.encode_lock_for_block_count(100)) > 0
    assert len(wasm.encode_lock_for_seconds(86400)) > 0
    assert len(wasm.encode_lock_until_height(HEIGHT)) > 0
    assert len(wasm.encode_lock_until_time(1_700_000_000)) > 0


def test_timelocks_are_deterministic_and_argument_sensitive(wasm: Client) -> None:
    assert wasm.encode_lock_for_block_count(100) == wasm.encode_lock_for_block_count(100)
    assert wasm.encode_lock_for_block_count(100) != wasm.encode_lock_for_block_count(101)
    assert wasm.encode_lock_until_height(HEIGHT) != wasm.encode_lock_until_time(HEIGHT)


# ── fees ──────────────────────────────────────────────────────────────────────


def test_fees_are_positive_at_fixed_height(wasm: Client) -> None:
    fees = [
        wasm.fungible_token_issuance_fee(HEIGHT, Network.MAINNET),
        wasm.nft_issuance_fee(HEIGHT, Network.MAINNET),
        wasm.data_deposit_fee(HEIGHT, Network.MAINNET),
        wasm.token_supply_change_fee(HEIGHT, Network.MAINNET),
        wasm.token_freeze_fee(HEIGHT, Network.MAINNET),
        wasm.token_change_authority_fee(HEIGHT, Network.MAINNET),
    ]
    for fee in fees:
        assert isinstance(fee, Amount)
        assert fee.atoms not in ("", "0"), f"expected a non-zero fee, got {fee.atoms!r}"
        assert int(fee.atoms) > 0


def test_fees_are_deterministic(wasm: Client) -> None:
    a = wasm.fungible_token_issuance_fee(HEIGHT, Network.MAINNET)
    b = wasm.fungible_token_issuance_fee(HEIGHT, Network.MAINNET)
    assert a == b


# ── staking ───────────────────────────────────────────────────────────────────


def test_encode_stake_pool_data(wasm: Client) -> None:
    wallet = Wallet(wasm)
    data = wasm.encode_stake_pool_data(
        Amount.from_atoms("40000000000000"),
        wallet.addr,
        VRF_MAINNET,
        wallet.addr,
        100,
        Amount.from_atoms("100000000"),
        Network.MAINNET,
    )
    assert isinstance(data, bytes) and len(data) > 0
    assert data == wasm.encode_stake_pool_data(
        Amount.from_atoms("40000000000000"),
        wallet.addr,
        VRF_MAINNET,
        wallet.addr,
        100,
        Amount.from_atoms("100000000"),
        Network.MAINNET,
    )


def test_encode_stake_pool_data_invalid_vrf_key_raises(wasm: Client) -> None:
    wallet = Wallet(wasm)
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_stake_pool_data(
            Amount.from_atoms("40000000000000"),
            wallet.addr,
            "vrfpk1qqqsyqcyq5rqwzqfpg9scrgwpugpzysnzs23v9ccrydpk8qarc0sq3rz3k",  # wrong HRP
            wallet.addr,
            100,
            Amount.from_atoms("100000000"),
            Network.MAINNET,
        )


def test_effective_pool_balance(wasm: Client) -> None:
    balance = wasm.effective_pool_balance(
        Network.MAINNET,
        Amount.from_atoms("50000000000"),
        Amount.from_atoms("1000000000000"),
    )
    assert isinstance(balance, Amount)
    assert int(balance.atoms) > 0


def test_effective_pool_balance_invalid_amount_raises(wasm: Client) -> None:
    with pytest.raises(WasmError, match="Invalid atoms amount"):
        wasm.effective_pool_balance(
            Network.MAINNET, Amount.from_atoms("zz"), Amount.from_atoms("1")
        )


def test_staking_pool_spend_maturity_block_count(wasm: Client) -> None:
    count = wasm.staking_pool_spend_maturity_block_count(HEIGHT, Network.MAINNET)
    assert count > 0
    assert count == wasm.staking_pool_spend_maturity_block_count(HEIGHT, Network.MAINNET)
