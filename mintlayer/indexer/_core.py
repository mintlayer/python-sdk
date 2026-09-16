"""Shared request helpers for the indexer client mixins."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from ._http import IndexerHTTP

__all__ = ["IndexerCore", "_seg"]


def _seg(value: Any) -> str:
    """URL-encode a path segment (defense against path traversal/injection)."""
    return quote(str(value), safe="")


class IndexerCore(IndexerHTTP):
    """Base class providing the typed request helpers used by the mixins."""

    def _get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        return self.get(path, query)

    def _post_text(self, path: str, body: str) -> Any:
        return self.post_text(path, body)
