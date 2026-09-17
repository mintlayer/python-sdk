"""Delegation endpoints (mirrors go-sdk/indexer/delegation.go)."""

from __future__ import annotations

from ._http import IndexerHTTP, _seg
from .types import Delegation


class DelegationMixin(IndexerHTTP):
    def get_delegation(self, delegation_id: str) -> Delegation:
        """Return a delegation by ID."""
        return Delegation.from_json(self.get(f"/delegation/{_seg(delegation_id)}"))
