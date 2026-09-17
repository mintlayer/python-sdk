"""Tests for indexer payload decoding (mintlayer.indexer.types).

Every ``from_json`` classmethod is wrapped so a malformed server payload
raises IndexerError — including payloads of the wrong JSON *shape* (a list
or scalar where an object is expected), which surface as AttributeError
inside the original decoders and must not leak out uncaught.
"""

from __future__ import annotations

import pytest

from mintlayer.indexer import Amount, IndexerError, Transaction
from mintlayer.indexer.types import BlockBody


@pytest.mark.parametrize(
    ("cls", "payload"),
    [
        pytest.param(Amount, ["list"], id="amount-list"),
        pytest.param(BlockBody, None, id="block-body-null"),
    ],
)
def test_from_json_non_object_payload_raises_indexer_error(cls: type, payload: object) -> None:
    """AttributeError from ``data.get`` on a non-dict is wrapped as IndexerError."""
    with pytest.raises(IndexerError, match=f"{cls.__name__}: malformed payload"):
        cls.from_json(payload)  # type: ignore[attr-defined]


def test_indexer_error_from_json_still_lists_transaction_fields() -> None:
    """Sanity: well-formed payloads keep decoding through the same wrapper."""
    tx = Transaction.from_json({"id": "tx01"})
    assert tx.id == "tx01"
