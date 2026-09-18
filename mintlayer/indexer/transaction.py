"""Transaction endpoints (mirrors go-sdk/indexer/transaction.go)."""

from __future__ import annotations

from typing import Any

from ._http import IndexerError, IndexerHTTP, _seg
from .types import MerklePath, PageOpts, Transaction


class TransactionMixin(IndexerHTTP):
    def list_transactions(self, opts: PageOpts | None = None) -> list[Transaction]:
        """List transactions with pagination."""
        data = self.get("/transaction", (opts or PageOpts()).query())
        return [Transaction.from_json(t) for t in data or []]

    def get_transaction(self, tx_id: str) -> Transaction:
        """Return a transaction by ID."""
        return Transaction.from_json(self.get(f"/transaction/{_seg(tx_id)}"))

    def get_transaction_merkle_path(self, tx_id: str) -> MerklePath:
        """Return the merkle path of a transaction (404 until it is in a block)."""
        return MerklePath.from_json(self.get(f"/transaction/{_seg(tx_id)}/merkle-path"))

    def get_transaction_output(self, tx_id: str, output_index: int) -> Any:
        """Return a transaction output as raw JSON (includes spent_at_block_height)."""
        return self.get(f"/transaction/{_seg(tx_id)}/output/{output_index}")

    def submit_transaction(self, signed_tx_hex: str) -> str:
        """Submit a signed transaction (hex) — requires ``--enable-post-routes``."""
        data = self.post_text("/transaction", signed_tx_hex)
        if not isinstance(data, dict) or "tx_id" not in data:
            raise IndexerError(f"submit_transaction: unexpected response {data!r}")
        return str(data["tx_id"])
