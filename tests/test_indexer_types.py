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


# ── Amount: both wire keys are now required ──────────────────────────────────


def _raw_amount_from_json():
    """The unwrapped ``Amount.from_json`` decoder (before _safe_from_json).

    The module wraps every registered class at import time; the original
    function is kept in the wrapper's closure so the raw KeyError semantics
    stay observable.
    """
    wrapper = Amount.from_json.__func__
    for cell in wrapper.__closure__ or ():
        candidate = cell.cell_contents
        if callable(candidate) and candidate is not wrapper:
            return candidate
    raise AssertionError("unwrapped Amount.from_json not found in closure")


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="both-keys-missing"),
        pytest.param({"atoms": "100"}, id="decimal-missing"),
        pytest.param({"decimal": "0.000001"}, id="atoms-missing"),
    ],
)
def test_amount_from_json_missing_key_raises_key_error(payload: dict) -> None:
    """A truncated payload raises KeyError in the raw decoder — no silent defaults."""
    raw = _raw_amount_from_json()
    with pytest.raises(KeyError):
        raw(Amount, payload)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="both-keys-missing"),
        pytest.param({"atoms": "100"}, id="decimal-missing"),
        pytest.param({"decimal": "0.000001"}, id="atoms-missing"),
    ],
)
def test_amount_from_json_missing_key_raises_indexer_error(payload: dict) -> None:
    """Through the _safe_from_json wrapper the same payload is an IndexerError."""
    with pytest.raises(IndexerError, match="Amount: malformed payload") as excinfo:
        Amount.from_json(payload)
    assert isinstance(excinfo.value.__cause__, KeyError)


def test_amount_from_json_both_keys_present_still_decodes() -> None:
    """A payload carrying both keys keeps decoding to a frozen Amount."""
    assert Amount.from_json({"atoms": "100", "decimal": "0.000001"}) == Amount(
        atoms="100", decimal="0.000001"
    )
