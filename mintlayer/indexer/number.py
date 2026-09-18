"""Lenient numeric decoding for indexer payloads (mirrors go-sdk/indexer/number.go).

The indexer documents several fields as integers/floats but the server
sometimes serialises them as strings (and even with a trailing ``%``).
"""

from __future__ import annotations

import math
import re
from typing import Any

from ._http import IndexerError

_DIGITS = re.compile(r"\d+")

__all__ = ["parse_uint64", "parse_per_thousand"]


def parse_uint64(data: Any) -> int:
    """Accept a bare JSON number or a decimal string; return an int."""
    if isinstance(data, bool):
        raise IndexerError(f"Uint64: invalid value {data!r}")
    if isinstance(data, int):
        if data < 0:
            raise IndexerError(f"Uint64: negative value {data!r}")
        return data
    if isinstance(data, str):
        if not _DIGITS.fullmatch(data):
            raise IndexerError(f"Uint64: invalid value {data!r}")
        if len(data) > 20 or (len(data) == 20 and data > "18446744073709551615"):
            # Cannot be a uint64 (max 18446744073709551615, 20 digits). Also
            # avoids the 3.11+ int-to-str digit limit raising a bare ValueError
            # for hostile oversized payloads.
            raise IndexerError(f"Uint64: value out of range {data!r}")
        return int(data, 10)
    raise IndexerError(f"Uint64: invalid value {data!r}")


def parse_per_thousand(data: Any) -> float:
    """Accept a bare number, a decimal string, or a string with a trailing %."""
    if isinstance(data, bool):
        raise IndexerError(f"PerThousand: invalid value {data!r}")
    if isinstance(data, (int, float)):
        value = float(data)
        if not math.isfinite(value):
            raise IndexerError(f"PerThousand: non-finite value {data!r}")
        return value
    if isinstance(data, str):
        stripped = data.strip('"')
        if stripped.endswith("%"):
            stripped = stripped[:-1]
        try:
            value = float(stripped)
        except ValueError as exc:
            raise IndexerError(f"PerThousand: {exc}") from exc
    else:
        raise IndexerError(f"PerThousand: invalid value {data!r}")
    if not math.isfinite(value):
        raise IndexerError(f"PerThousand: non-finite value {data!r}")
    return value
