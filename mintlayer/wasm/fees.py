"""Fee queries (mirrors go-sdk/wasm/fees.go)."""

from __future__ import annotations

from ._core import _WasmCore
from ._util import synchronized
from .types import Amount, Network


class FeesMixin(_WasmCore):
    @synchronized
    def fungible_token_issuance_fee(self, current_block_height: int, network: Network) -> Amount:
        """Fee required to issue a new fungible token at the given block height."""
        return self._call_return_amount(
            "fungible_token_issuance_fee", current_block_height, int(network)
        )

    @synchronized
    def nft_issuance_fee(self, current_block_height: int, network: Network) -> Amount:
        """Fee required to issue a new NFT at the given block height."""
        return self._call_return_amount("nft_issuance_fee", current_block_height, int(network))

    @synchronized
    def data_deposit_fee(self, current_block_height: int, network: Network) -> Amount:
        """Fee required to create a DataDeposit output at the given block height."""
        return self._call_return_amount("data_deposit_fee", current_block_height, int(network))

    @synchronized
    def token_supply_change_fee(self, current_block_height: int, network: Network) -> Amount:
        """Fee required to mint or unmint tokens at the given block height."""
        return self._call_return_amount(
            "token_supply_change_fee", current_block_height, int(network)
        )

    @synchronized
    def token_freeze_fee(self, current_block_height: int, network: Network) -> Amount:
        """Fee required to freeze or unfreeze a token at the given block height."""
        return self._call_return_amount("token_freeze_fee", current_block_height, int(network))

    @synchronized
    def token_change_authority_fee(self, current_block_height: int, network: Network) -> Amount:
        """Fee required to change a token's authority at the given block height."""
        return self._call_return_amount(
            "token_change_authority_fee", current_block_height, int(network)
        )
