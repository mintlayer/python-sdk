"""Chain endpoints (mirrors go-sdk/indexer/chain.go)."""

from __future__ import annotations

from ._http import IndexerHTTP, _seg
from .types import ChainTip, GenesisInfo


class ChainMixin(IndexerHTTP):
    def get_tip(self) -> ChainTip:
        """Return the current chain tip."""
        return ChainTip.from_json(self.get("/chain/tip"))

    def get_genesis(self) -> GenesisInfo:
        """Return genesis block info."""
        return GenesisInfo.from_json(self.get("/chain/genesis"))

    def get_block_id_at_height(self, height: int) -> str:
        """Return the block ID at ``height`` (raises HTTPError 404 if unknown)."""
        result = self.get(f"/chain/{_seg(height)}")
        return "" if result is None else str(result)
