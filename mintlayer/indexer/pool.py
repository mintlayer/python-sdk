"""Pool endpoints (mirrors go-sdk/indexer/pool.go)."""

from __future__ import annotations

from datetime import datetime

from ._core import IndexerCore, _seg
from .types import Pool, PoolDelegation, PoolListOpts


class PoolMixin(IndexerCore):
    def list_pools(self, opts: PoolListOpts | None = None) -> list[Pool]:
        """List staking pools with pagination and optional sort."""
        data = self._get("/pool", (opts or PoolListOpts()).query())
        return [Pool.from_json(p) for p in data or []]

    def get_pool(self, pool_id: str) -> Pool:
        """Return a staking pool by ID."""
        return Pool.from_json(self._get(f"/pool/{_seg(pool_id)}"))

    def get_pool_block_stats(self, pool_id: str, from_time: datetime, to_time: datetime) -> int:
        """Return the block count produced in the half-open interval [from, to)."""
        data = self._get(
            f"/pool/{_seg(pool_id)}/block-stats",
            {"from": int(from_time.timestamp()), "to": int(to_time.timestamp())},
        )
        return int(data["block_count"])

    def get_pool_delegations(self, pool_id: str) -> list[PoolDelegation]:
        """Return the delegations to a pool."""
        data = self._get(f"/pool/{_seg(pool_id)}/delegations")
        return [PoolDelegation.from_json(d) for d in data or []]
