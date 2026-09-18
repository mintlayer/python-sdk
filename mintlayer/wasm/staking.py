"""Staking helpers (mirrors go-sdk/wasm/staking.go)."""

from __future__ import annotations

from ._core import _WasmCore
from ._util import synchronized
from .types import Amount, Network


class StakingMixin(_WasmCore):
    @synchronized
    def encode_stake_pool_data(
        self,
        value: Amount,
        staker: str,
        vrf_public_key: str,
        decommission_key: str,
        margin_ratio_per_thousand: int,
        cost_per_block: Amount,
        network: Network,
    ) -> bytes:
        """Encode the parameters of a staking pool into binary form.

        Suitable for use in ``encode_output_create_stake_pool``.

        ``staker`` is the bech32m address allowed to produce blocks.
        ``vrf_public_key`` is the bech32m-encoded VRF public key for the pool.
        ``decommission_key`` is the bech32m address that can decommission the pool.
        ``margin_ratio_per_thousand`` is the share of block rewards kept by the
        staker (0-1000).
        ``cost_per_block`` is a fixed amount subtracted from block rewards
        before margin calculation.
        """
        val_ptr = self._new_wasm_amount(value)
        staker_ptr, staker_len = self._write_string(staker)
        vrf_ptr, vrf_len = self._write_string(vrf_public_key)
        decomm_ptr, decomm_len = self._write_string(decommission_key)
        cpb_ptr = self._new_wasm_amount(cost_per_block)
        return self._call_return_bytes(
            "encode_stake_pool_data",
            val_ptr,
            staker_ptr,
            staker_len,
            vrf_ptr,
            vrf_len,
            decomm_ptr,
            decomm_len,
            margin_ratio_per_thousand,
            cpb_ptr,
            int(network),
        )

    @synchronized
    def effective_pool_balance(
        self, network: Network, pledge_amount: Amount, pool_balance: Amount
    ) -> Amount:
        """Compute the effective balance of a staking pool used for stake selection."""
        pledge_ptr = self._new_wasm_amount(pledge_amount)
        pool_ptr = self._new_wasm_amount(pool_balance)
        return self._call_return_amount_fallible(
            "effective_pool_balance", int(network), pledge_ptr, pool_ptr
        )

    @synchronized
    def staking_pool_spend_maturity_block_count(
        self, current_block_height: int, network: Network
    ) -> int:
        """Blocks that must pass after a pool decommissions before funds are spendable."""
        return self._call_return_u64(
            "staking_pool_spend_maturity_block_count", current_block_height, int(network)
        )
