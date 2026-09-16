"""Statistics endpoints (mirrors go-sdk/indexer/statistics.go)."""

from __future__ import annotations

from ._core import IndexerCore
from .types import CoinStats


class StatisticsMixin(IndexerCore):
    def get_coin_statistics(self) -> CoinStats:
        """Return circulating/preminted/burned/staked coin totals."""
        return CoinStats.from_json(self._get("/statistics/coin"))

    def get_token_statistics(self, token_id: str) -> CoinStats:
        """Return the same statistics for a token."""
        return CoinStats.from_json(self._get(f"/statistics/token/{token_id}"))

    def get_fee_rate(self, in_top_x_mb: int = 0) -> str:
        """Return the fee rate (atoms per KB) as a decimal string.

        ``in_top_x_mb`` is omitted when zero, using the server default (5 MB).
        """
        query = {"in_top_x_mb": in_top_x_mb} if in_top_x_mb > 0 else None
        result = self._get("/feerate", query)
        return "" if result is None else str(result)
