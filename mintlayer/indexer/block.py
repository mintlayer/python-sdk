"""Block endpoints (mirrors go-sdk/indexer/block.go)."""

from __future__ import annotations

from ._http import IndexerHTTP, _seg
from .types import Block, BlockHeader


class BlockMixin(IndexerHTTP):
    def get_block(self, block_id: str) -> Block:
        """Return a block with header and body."""
        return Block.from_json(self.get(f"/block/{_seg(block_id)}"))

    def get_block_header(self, block_id: str) -> BlockHeader:
        """Return a block header."""
        return BlockHeader.from_json(self.get(f"/block/{_seg(block_id)}/header"))

    def get_block_reward(self, block_id: str) -> list:
        """Return the block reward outputs (raw JSON list)."""
        return self.get(f"/block/{_seg(block_id)}/reward") or []

    def get_block_transaction_ids(self, block_id: str) -> list[str]:
        """Return the transaction IDs included in a block."""
        return self.get(f"/block/{_seg(block_id)}/transaction-ids") or []
