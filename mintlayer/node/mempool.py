"""Mempool methods (mirrors go-sdk/node/mempool.go)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._core import _NodeCore
from .types import FeeRate, FeeRatePoint, MempoolTx, TrustPolicy
from .types import policy_value as _policy_value

if TYPE_CHECKING:
    pass


class MempoolMixin(_NodeCore):
    def contains_tx(self, tx_id: str) -> bool:
        """Return whether the transaction is in the mempool."""
        return self._call_bool("mempool_contains_tx", {"tx_id": tx_id})

    def contains_orphan_tx(self, tx_id: str) -> bool:
        """Return whether the transaction is in the orphan pool."""
        return self._call_bool("mempool_contains_orphan_tx", {"tx_id": tx_id})

    def get_transaction(self, tx_id: str) -> MempoolTx | None:
        """Return the mempool transaction (None if not present)."""
        data = self._call("mempool_get_transaction", {"tx_id": tx_id})
        return MempoolTx.from_json(data) if data is not None else None

    def mempool_submit_transaction(self, tx_hex: str, trust_policy: TrustPolicy | str) -> None:
        """Submit a transaction to the local mempool only (no P2P broadcast).

        Use ``TrustPolicy.UNTRUSTED`` (recommended) for full validation;
        ``TrustPolicy.TRUSTED`` skips some fee checks.
        """
        self._call_ignore(
            "mempool_submit_transaction",
            {"tx": tx_hex, "options": {"trust_policy": _policy_value(trust_policy)}},
        )

    def get_fee_rate(self, in_top_x_mb: int) -> FeeRate | None:
        """Return the fee rate to land in the top ``in_top_x_mb`` MB of the mempool."""
        data = self._call("mempool_get_fee_rate", {"in_top_x_mb": in_top_x_mb})
        return FeeRate.from_json(data) if data is not None else None

    def get_fee_rate_points(self) -> list[FeeRatePoint]:
        """Return the mempool fee rate histogram."""
        data = self._call("mempool_get_fee_rate_points", {})
        return [FeeRatePoint.from_json(item) for item in data or []]

    def memory_usage(self) -> int:
        """Return the mempool memory usage in bytes."""
        return self._call_int("mempool_memory_usage", {})
