"""Chainstate methods (mirrors go-sdk/node/chainstate.go).

Not-found results (JSON ``null``) map to ``None``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._core import _NodeCore
from .types import Amount, ChainstateInfo, Currency, OrderInfo, Outpoint, TokenInfo

if TYPE_CHECKING:
    pass


class ChainstateMixin(_NodeCore):
    def chainstate_info(self) -> ChainstateInfo:
        """Return the current chainstate summary."""
        return ChainstateInfo.from_json(self._call("chainstate_info", {}))

    def best_block_id(self) -> str:
        """Return the best block ID (hex, no 0x prefix)."""
        return self._call_str("chainstate_best_block_id", {})

    def best_block_height(self) -> int:
        """Return the best block height."""
        return self._call_int("chainstate_best_block_height", {})

    def block_id_at_height(self, height: int) -> str | None:
        """Return the block ID at ``height`` (None if the height is unknown)."""
        return self._call_opt_str("chainstate_block_id_at_height", {"height": height})

    def block_height_in_main_chain(self, block_id: str) -> int | None:
        """Return the height of ``block_id`` in the mainchain (None if orphaned)."""
        return self._call_opt_int("chainstate_block_height_in_main_chain", {"block_id": block_id})

    def get_block(self, block_id: str) -> str | None:
        """Return the hex-encoded block (None if unknown; genesis not retrievable)."""
        return self._call_opt_str("chainstate_get_block", {"id": block_id})

    def get_block_json(self, block_id: str) -> Any:
        """Return the block as decoded JSON (None if unknown)."""
        return self._call("chainstate_get_block_json", {"id": block_id})

    def get_mainchain_blocks(self, from_height: int, max_count: int) -> list[str]:
        """Return up to ``max_count`` mainchain block IDs starting at ``from_height``."""
        return self._call_str_list(
            "chainstate_get_mainchain_blocks",
            {"from": from_height, "max_count": max_count},
        )

    def get_utxo(self, outpoint: Outpoint) -> Any:
        """Return the UTXO at ``outpoint`` as decoded JSON (None if spent/unknown)."""
        return self._call("chainstate_get_utxo", {"outpoint": outpoint.to_json()})

    def stake_pool_balance(self, pool_address: str) -> Amount | None:
        """Return the pledge balance of the pool (None if the pool is unknown)."""
        return self._call_opt_amount(
            "chainstate_stake_pool_balance", {"pool_address": pool_address}
        )

    def staker_balance(self, pool_address: str) -> Amount | None:
        """Return the staker's balance of the pool (None if the pool is unknown)."""
        return self._call_opt_amount("chainstate_staker_balance", {"pool_address": pool_address})

    def pool_decommission_destination(self, pool_address: str) -> str | None:
        """Return the address that receives funds on decommission."""
        return self._call_opt_str(
            "chainstate_pool_decommission_destination", {"pool_address": pool_address}
        )

    def delegation_share(self, pool_address: str, delegation_address: str) -> Amount | None:
        """Return the delegation share held by ``delegation_address``."""
        return self._call_opt_amount(
            "chainstate_delegation_share",
            {"pool_address": pool_address, "delegation_address": delegation_address},
        )

    def token_info(self, token_id: str) -> TokenInfo | None:
        """Return token info (tagged union; None if unknown)."""
        data = self._call("chainstate_token_info", {"token_id": token_id})
        return TokenInfo.from_json(data) if data is not None else None

    def tokens_info(self, token_ids: list[str]) -> list[TokenInfo]:
        """Return info for multiple token IDs."""
        data = self._call("chainstate_tokens_info", {"token_ids": token_ids})
        return [TokenInfo.from_json(item) for item in data or []]

    def order_info(self, order_id: str) -> OrderInfo | None:
        """Return order info (None if unknown)."""
        data = self._call("chainstate_order_info", {"order_id": order_id})
        return OrderInfo.from_json(data) if data is not None else None

    def orders_info_by_currencies(
        self, ask: Currency | None, give: Currency | None
    ) -> dict[str, OrderInfo]:
        """Return orders matching the ask/give currency filters (None = any).

        Both keys are always sent; ``None`` serialises as JSON ``null``.
        """
        data = self._call(
            "chainstate_orders_info_by_currencies",
            {
                "ask_currency": ask.to_json() if ask is not None else None,
                "give_currency": give.to_json() if give is not None else None,
            },
        )
        return {k: OrderInfo.from_json(v) for k, v in (data or {}).items()}

    def submit_block(self, block_hex: str) -> None:
        """Submit a fully serialized block (hex)."""
        self._call_ignore("chainstate_submit_block", {"block_hex": block_hex})
