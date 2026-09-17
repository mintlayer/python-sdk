"""Staking and delegation methods (mirrors go-sdk/wallet/staking.go)."""

from __future__ import annotations

from ._core import _WalletCore
from .types import (
    Amount,
    CreateDelegationParams,
    CreateDelegationResult,
    CreatePoolParams,
    DecommissionParams,
    DelegateParams,
    DelegationInfo,
    OwnedPool,
    SendResult,
    StakingStatus,
    WithdrawParams,
)


class StakingMixin(_WalletCore):
    def create_stake_pool(self, params: CreatePoolParams) -> SendResult:
        """Create a new staking pool."""
        return self._call_model("staking_create_pool", params.to_json(), SendResult)

    def decommission_stake_pool(self, params: DecommissionParams) -> SendResult:
        """Decommission a stake pool the account owns."""
        return self._call_model("staking_decommission_pool", params.to_json(), SendResult)

    def list_owned_pools(self, account: int) -> list[OwnedPool]:
        """List the pools owned by the account."""
        return self._call_model_list("staking_list_pools", {"account": account}, OwnedPool)

    def get_pool_balance(self, account: int, pool_id: str) -> Amount:
        """Return a pool's balance.

        Note: matching the daemon route, ``account`` is accepted for API
        consistency but NOT sent on the wire.
        """
        data = self._call("staking_pool_balance", {"pool_id": pool_id})
        return Amount.from_json((data or {}).get("balance", {}))

    def start_staking(self, account: int) -> None:
        """Start staking with all of the account's pools."""
        self._call_ignore("staking_start", {"account": account})

    def stop_staking(self, account: int) -> None:
        """Stop staking for the account."""
        self._call_ignore("staking_stop", {"account": account})

    def get_staking_status(self, account: int) -> StakingStatus:
        """Return whether the account is currently staking."""
        result = self._call("staking_status", {"account": account})
        return StakingStatus(result)

    def create_delegation(self, params: CreateDelegationParams) -> CreateDelegationResult:
        """Create a delegation ID for delegating to a pool."""
        return self._call_model("delegation_create", params.to_json(), CreateDelegationResult)

    def delegate_staking(self, params: DelegateParams) -> SendResult:
        """Delegate coins to a pool via a delegation ID."""
        return self._call_model("delegation_stake", params.to_json(), SendResult)

    def withdraw_from_delegation(self, params: WithdrawParams) -> SendResult:
        """Withdraw from a delegation to an address."""
        return self._call_model("delegation_withdraw", params.to_json(), SendResult)

    def list_delegations(self, account: int) -> list[DelegationInfo]:
        """List the account's delegation IDs and balances."""
        return self._call_model_list("delegation_list_ids", {"account": account}, DelegationInfo)
