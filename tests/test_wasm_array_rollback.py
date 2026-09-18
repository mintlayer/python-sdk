"""Tests for the pre-call rollback branches of the externref array writers.

Fault injection (mirroring test_wasm_lifecycle.py) forces mid-loop failures
in ``_write_string_array`` / ``_write_uint8_array_array`` (``table.set``
raising) and in ``estimate_transaction_size`` (``_write_bytes`` raising on
the outputs write) so the host-side rollback branches run: the
already-allocated externref table slots must be released via
``_dealloc_indices`` (reading back null and handed out again by the
allocator), backing buffers freed, the original exception re-raised, and the
client left fully usable.
"""

from __future__ import annotations

from typing import Any

import pytest
from wasm_helpers import Wallet, fake_input
from wasmtime import Val

from mintlayer.wasm import Amount, Client, Network

# ── fault-injection helpers ───────────────────────────────────────────────────


class TableSetFailsNth:
    """Proxy for the externref table that fails the Nth ``set()`` call.

    Mirrors the ``MemorySpy`` pattern (instance attribute replacing the real
    object): everything except ``set()`` is delegated to the real wasmtime
    table. Slot indices are recorded for every ``set()`` attempt, including
    the failing one, so tests know exactly which slots the rollback must
    release.
    """

    def __init__(self, real: Any, fail_on: int) -> None:
        self._real = real
        self._fail_on = fail_on
        self._calls = 0
        self.attempted_indices: list[int] = []
        self.error = RuntimeError("injected table.set failure")

    def set(self, store: Any, idx: int, value: Any) -> None:
        self._calls += 1
        self.attempted_indices.append(idx)
        if self._calls == self._fail_on:
            raise self.error
        self._real.set(store, idx, value)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


def _is_null_anyref(value: object) -> bool:
    """True when wasmtime reports a table slot as null/undefined (released)."""
    if value is None:
        return True
    if isinstance(value, Val):
        return value.__dict__.get("_val", object()) is None
    return False


def _alloc_reusable_slot(c: Client) -> int:
    """Allocate one externref-table slot from the reusable (recycled) region.

    Mirrors the helper in test_wasm_transactions.py: the module's lowest
    table indices form a permanent slab that ``__externref_table_dealloc``
    deliberately does not recycle. Probing until a freed slot is handed out
    again guarantees the free list is active, making later slot-reuse
    assertions deterministic regardless of prior table state.
    """
    for _ in range(512):
        probe = c._invoke1("__externref_table_alloc")
        c._dealloc_indices([probe])
        if c._invoke1("__externref_table_alloc") == probe:
            return probe
    raise AssertionError("no reusable externref table slot found")


def _assert_rolled_back_slots_released(c: Client, released: set[int]) -> None:
    """Every rolled-back slot reads back null and is handed out again."""
    for idx in released:
        assert _is_null_anyref(c.table.get(c.store, idx)), f"slot {idx} still holds a value"
    for _ in range(512):
        probe = c._invoke1("__externref_table_alloc")
        c._dealloc_indices([probe])
        if probe in released:
            return
    raise AssertionError(f"none of the rolled-back slots {sorted(released)} was reused")


# ── _write_string_array rollback ──────────────────────────────────────────────


def test_write_string_array_rollback_releases_slots_on_mid_loop_failure(
    wasm: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``table.set`` raising on the 2nd element rolls back every slot so far."""
    _alloc_reusable_slot(wasm)  # make slot-reuse assertions deterministic
    table_spy = TableSetFailsNth(wasm.table, fail_on=2)
    monkeypatch.setattr(wasm, "table", table_spy)

    with pytest.raises(RuntimeError) as excinfo:
        wasm._write_string_array(["a", "b", "c"])

    # The original injected exception propagated: the rollback neither
    # swallowed nor replaced it.
    assert excinfo.value is table_spy.error
    # Two slots were allocated before the failure (2nd set() raised); both
    # were appended to the indices list and must have been released.
    assert len(table_spy.attempted_indices) == 2
    _assert_rolled_back_slots_released(wasm, set(table_spy.attempted_indices))


# ── _write_uint8_array_array rollback ─────────────────────────────────────────


def test_write_uint8_array_array_rollback_releases_slots_and_buffers(
    wasm: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``table.set`` raising rolls back slots AND frees the backing buffers."""
    _alloc_reusable_slot(wasm)
    table_spy = TableSetFailsNth(wasm.table, fail_on=2)
    monkeypatch.setattr(wasm, "table", table_spy)

    writes: list[tuple[int, int]] = []
    frees: list[tuple[int, int]] = []
    original_write_bytes = wasm._write_bytes
    original_free_wasm = wasm._free_wasm

    def recording_write_bytes(data: bytes) -> tuple[int, int]:
        result = original_write_bytes(data)
        writes.append(result)
        return result

    def recording_free_wasm(ptr: int, size: int, align: int = 1) -> None:
        frees.append((ptr, size))
        original_free_wasm(ptr, size, align)

    monkeypatch.setattr(wasm, "_write_bytes", recording_write_bytes)
    monkeypatch.setattr(wasm, "_free_wasm", recording_free_wasm)

    with pytest.raises(RuntimeError) as excinfo:
        wasm._write_uint8_array_array([b"slice-0", b"slice-1", b"slice-2"])

    assert excinfo.value is table_spy.error
    # One backing buffer per attempted slice: both were written before the
    # failure and both must have been freed by the rollback (buffer free is
    # best-effort host-side; the free call itself must have been made).
    assert len(writes) == 2
    for buffer in writes:
        assert buffer in frees
    # Every externref slot touched before the failure is released too.
    assert len(table_spy.attempted_indices) == 2
    _assert_rolled_back_slots_released(wasm, set(table_spy.attempted_indices))


# ── estimate_transaction_size narrow rollback ─────────────────────────────────


def test_estimate_transaction_size_rollback_leaves_client_usable(
    wasm: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_write_bytes`` failing on the outputs write rolls the dest slots back.

    The narrow rollback in ``estimate_transaction_size`` must release the
    destination slots allocated by ``_write_string_array`` (the callee never
    ran, so the host still owns them) and leave the client fully usable.
    """
    wallet = Wallet(wasm)
    inputs = fake_input(wasm)
    outputs = wasm.encode_output_transfer(
        Amount.from_atoms("100000000000"), wallet.addr, Network.MAINNET
    )
    tx = wasm.encode_transaction(inputs, outputs, 0)

    _alloc_reusable_slot(wasm)  # make the table-size invariant deterministic
    warm = wasm.estimate_transaction_size(tx, [wallet.addr], outputs, Network.MAINNET)
    assert warm > 0
    baseline_table = wasm.table.size(wasm.store)

    boom = RuntimeError("injected outputs write failure")
    calls = {"count": 0}
    original_write_bytes = wasm._write_bytes
    original_string_array = wasm._write_string_array
    array_indices: list[list[int]] = []

    def fail_on_second_write(data: bytes) -> tuple[int, int]:
        calls["count"] += 1
        if calls["count"] == 2:
            raise boom
        return original_write_bytes(data)

    def recording_string_array(strs: list[str]) -> tuple[int, list[int]]:
        result = original_string_array(strs)
        array_indices.append(result[1])
        return result

    monkeypatch.setattr(wasm, "_write_bytes", fail_on_second_write)
    monkeypatch.setattr(wasm, "_write_string_array", recording_string_array)

    # inputs write (1st call) succeeds, the destinations array write
    # succeeds, outputs write (2nd call) fails → rollback must run.
    with pytest.raises(RuntimeError) as excinfo:
        wasm.estimate_transaction_size(tx, [wallet.addr], outputs, Network.MAINNET)
    assert excinfo.value is boom
    assert calls["count"] == 2
    assert len(array_indices) == 1 and len(array_indices[0]) == 1
    # The narrow rollback must have released the destination slot already:
    # the callee never ran, so the host still owns it. It reads back null
    # and is handed out again by the allocator — not leaked.
    _assert_rolled_back_slots_released(wasm, set(array_indices[0]))

    # The client is fully usable afterwards: the next real estimate succeeds
    # with the very same result, and the externref table did not grow — the
    # rolled-back slot was recycled, not leaked.
    recovered = wasm.estimate_transaction_size(tx, [wallet.addr], outputs, Network.MAINNET)
    assert recovered == warm
    assert wasm.table.size(wasm.store) == baseline_table
