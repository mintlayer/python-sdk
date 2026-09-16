"""Delegation endpoints (mirrors go-sdk/indexer/delegation.go)."""

from __future__ import annotations

from ._core import IndexerCore, _seg
from .types import Delegation


class DelegationMixin(IndexerCore):
    def get_delegation(self, delegation_id: str) -> Delegation:
        """Return a delegation by ID."""
        return Delegation.from_json(self._get(f"/delegation/{_seg(delegation_id)}"))
