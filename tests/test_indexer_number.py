"""Tests for the lenient numeric decoders (mintlayer.indexer.number).

Mirrors go-sdk/indexer/number.go semantics: out-of-contract payload shapes
must raise IndexerError (the library's codec failure), never a bare
TypeError from float()/str conversion.
"""

from __future__ import annotations

import pytest

from mintlayer.indexer import IndexerError
from mintlayer.indexer.number import parse_per_thousand


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(None, id="null"),
        pytest.param([1], id="list"),
    ],
)
def test_parse_per_thousand_non_scalar_raises_indexer_error(data: object) -> None:
    """None/list payloads raise IndexerError instead of a bare TypeError."""
    with pytest.raises(IndexerError, match="PerThousand: invalid value"):
        parse_per_thousand(data)
