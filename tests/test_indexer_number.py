"""Tests for the lenient numeric decoders (mintlayer.indexer.number).

Mirrors go-sdk/indexer/number.go semantics: out-of-contract payload shapes
must raise IndexerError (the library's codec failure), never a bare
TypeError from float()/str conversion.
"""

from __future__ import annotations

import pytest

from mintlayer.indexer import IndexerError
from mintlayer.indexer.number import parse_per_thousand, parse_uint64


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


@pytest.mark.parametrize(
    "data",
    [
        pytest.param("1" * 21, id="21_digits"),
        pytest.param("18446744073709551616", id="uint64_max_plus_one"),
    ],
)
def test_parse_uint64_overlong_numeric_string_raises_indexer_error(data: str) -> None:
    """Numeric strings longer than 20 digits cannot be uint64 values."""
    with pytest.raises(IndexerError, match="out of range"):
        parse_uint64(data)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param("0", 0, id="zero"),
        pytest.param("18446744073709551615", 18446744073709551615, id="uint64_max"),
    ],
)
def test_parse_uint64_boundary_string_parses(data: str, expected: int) -> None:
    """20-digit values up to the uint64 maximum must still parse fine."""
    assert parse_uint64(data) == expected
