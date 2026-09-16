"""Address endpoints (mirrors go-sdk/indexer/address.go)."""

from __future__ import annotations

from ._core import IndexerCore, _seg
from .types import UTXO, AddressInfo, DelegationInfo


class AddressMixin(IndexerCore):
    def get_address_info(self, address: str) -> AddressInfo:
        """Return address balances and history (404 if the address has none)."""
        return AddressInfo.from_json(self._get(f"/address/{_seg(address)}"))

    def get_spendable_utxos(self, address: str) -> list[UTXO]:
        """Return the address's spendable UTXOs."""
        data = self._get(f"/address/{_seg(address)}/spendable-utxos")
        return [UTXO.from_json(u) for u in data or []]

    def get_all_utxos(self, address: str) -> list[UTXO]:
        """Return all UTXOs for the address (including timelocked)."""
        data = self._get(f"/address/{_seg(address)}/all-utxos")
        return [UTXO.from_json(u) for u in data or []]

    def get_delegations(self, address: str) -> list[DelegationInfo]:
        """Return the delegations created by the address."""
        data = self._get(f"/address/{_seg(address)}/delegations")
        return [DelegationInfo.from_json(d) for d in data or []]

    def get_token_authority(self, address: str) -> list[str]:
        """Return the bech32 token IDs the address has authority over."""
        return self._get(f"/address/{_seg(address)}/token-authority") or []
