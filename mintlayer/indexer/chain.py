"""Chain endpoints (mirrors go-sdk/indexer/chain.go)."""

from __future__ import annotations

from ._core import IndexerCore, _seg
from .types import ChainTip, GenesisInfo


class ChainMixin(IndexerCore):
    def get_tip(self) -> ChainTip:
        """Return the current chain tip."""
        return ChainTip.from_json(self._get("/chain/tip"))

    def get_genesis(self) -> GenesisInfo:
        """Return genesis block info."""
        return GenesisInfo.from_json(self._get("/chain/genesis"))

    def get_block_id_at_height(self, height: int) -> str:
        """Return the block ID at ``height`` (raises HTTPError 404 if unknown)."""
        result = self._get(f"/chain/{_seg(height)}")
        return "" if result is None else str(result)
