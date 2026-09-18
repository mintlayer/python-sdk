"""Tests for WASM client lifecycle and the low-level _core machinery.

Covers instantiation, close()/context-manager semantics, closed-client
errors, the sha256 integrity pin, call-convention edge cases reachable from
Python (unknown exports, unexpected return counts, memory-read failures),
and the documented result-buffer zeroing behaviour.
"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

import pytest
from wasm_helpers import MemorySpy

from mintlayer.wasm import Client, Network, WasmError
from mintlayer.wasm import _core as wasm_core

# ── integrity pin ─────────────────────────────────────────────────────────────


def test_integrity_pin_file_matches_binary() -> None:
    """The vendored WASM binary matches its committed sha256 pin."""
    pin_path = wasm_core._WASM_PATH.with_suffix(".wasm.sha256")
    assert pin_path.exists(), "sha256 pin file must be shipped next to the binary"
    expected = pin_path.read_text().split()[0].strip()
    actual = hashlib.sha256(wasm_core._WASM_BYTES).hexdigest()
    assert actual == expected
    # Reloading through the loader exercises the same verify path as import.
    assert wasm_core._load_and_verify_wasm() == wasm_core._WASM_BYTES


def test_integrity_pin_rejects_tampered_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A binary whose hash differs from the pin fails closed."""
    wasm_file = tmp_path / "fake.wasm"
    wasm_file.write_bytes(b"tampered")
    original = hashlib.sha256(b"original").hexdigest()
    wasm_file.with_suffix(".wasm.sha256").write_text(f"{original}\n")
    monkeypatch.setattr(wasm_core, "_WASM_PATH", wasm_file)
    with pytest.raises(WasmError, match="integrity check failed"):
        wasm_core._load_and_verify_wasm()


def test_missing_pin_file_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A binary without its sha256 pin file is a packaging error."""
    wasm_file = tmp_path / "fake.wasm"
    wasm_file.write_bytes(b"binary")
    monkeypatch.setattr(wasm_core, "_WASM_PATH", wasm_file)  # no .sha256 written
    with pytest.raises(WasmError, match="pin file missing"):
        wasm_core._load_and_verify_wasm()


def test_empty_pin_file_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty pin file pins nothing and must not pass verification."""
    wasm_file = tmp_path / "fake.wasm"
    wasm_file.write_bytes(b"binary")
    wasm_file.with_suffix(".wasm.sha256").write_text("")
    monkeypatch.setattr(wasm_core, "_WASM_PATH", wasm_file)
    with pytest.raises(WasmError, match="pin file is empty"):
        wasm_core._load_and_verify_wasm()


# ── lifecycle ─────────────────────────────────────────────────────────────────


def test_instantiation_and_basic_call() -> None:
    c = Client()
    try:
        assert c.make_private_key()
    finally:
        c.close()


def test_context_manager_closes() -> None:
    with Client() as c:
        c.make_private_key()
    with pytest.raises(WasmError, match="closed"):
        c.make_private_key()


def test_close_is_idempotent() -> None:
    c = Client()
    c.make_private_key()
    c.close()
    c.close()


def test_closed_client_rejects_calls() -> None:
    c = Client()
    c.close()
    with pytest.raises(WasmError, match="closed"):
        c.make_private_key()


def test_get_export_after_close_is_none() -> None:
    c = Client()
    c.close()
    assert c.get_export("make_private_key") is None


# ── export lookup / low-level call conventions ────────────────────────────────


def test_call_unknown_export(wasm: Client) -> None:
    with pytest.raises(WasmError, match='function "no_such_export" not found'):
        wasm._call("no_such_export")


def test_fn_lookup_unknown_export_open_client(wasm: Client) -> None:
    with pytest.raises(WasmError, match="not found"):
        wasm._fn("no_such_export")


def test_call_return_bytes_unexpected_count(wasm: Client) -> None:
    wasm._exports["fake_no_ret"] = lambda store: None
    try:
        with pytest.raises(WasmError, match="unexpected return count"):
            wasm._call_return_bytes("fake_no_ret")
        with pytest.raises(WasmError, match="unexpected return count"):
            wasm._call_return_string("fake_no_ret")
        with pytest.raises(WasmError, match="unexpected return count"):
            wasm._call_return_bytes_no_err("fake_no_ret")
    finally:
        del wasm._exports["fake_no_ret"]


def test_call_return_json_without_json_result(
    wasm: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A successful call that captured no JSON payload is an error."""
    monkeypatch.setattr(wasm, "_call", lambda name, *params: [0, 0])
    with pytest.raises(WasmError, match="no JSON result"):
        wasm._call_return_json("fake_json_fn")


def test_read_bytes_out_of_bounds_is_empty(wasm: Client) -> None:
    """Out-of-bounds reads are clamped to an empty buffer by wasmtime."""
    data = wasm._read_bytes(0xFFFF_FFFF, 16)
    assert data is not None and len(data) == 0


def test_memory_read_failure(wasm: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    """If the result buffer cannot be read back, callers get a clear error."""
    pub = wasm.public_key_from_private_key(wasm.make_private_key())
    monkeypatch.setattr(wasm, "_read_bytes", lambda ptr, length: None)
    with pytest.raises(WasmError, match="memory read failed"):
        wasm.pubkey_to_pubkeyhash_address(pub, Network.MAINNET)


def test_no_return_value_from_amount_call(wasm: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wasm, "_call", lambda name, *params: [])
    with pytest.raises(WasmError, match="no return value"):
        wasm._call_return_amount("fake_amount_fn")
    with pytest.raises(WasmError, match="no return value"):
        wasm._call_return_amount_fallible("fake_amount_fn")


def test_memory_helpers_edge_cases(wasm: Client) -> None:
    """Empty/None writes are the (0, 0) null pair; freeing null is a no-op."""
    assert wasm._write_bytes(b"") == (0, 0)
    assert wasm._write_string("") == (0, 0)
    assert wasm._write_optional_string(None) == (0, 0)
    assert wasm._write_optional_bytes(None) == (0, 0)
    wasm._free_wasm(0, 128)  # null pointer: must not touch the allocator
    wasm._dealloc_indices([])  # empty: no table slots to release


def test_write_bytes_roundtrip(wasm: Client) -> None:
    ptr, length = wasm._write_bytes(b"payload")
    try:
        assert length == len(b"payload")
        data = wasm.memory.read(wasm.store, ptr, ptr + length)
        assert data is not None and bytes(data) == b"payload"
    finally:
        wasm._free_wasm(ptr, length)


# ── memory hygiene ────────────────────────────────────────────────────────────


def test_result_buffers_are_zeroed_before_release(wasm: Client) -> None:
    """Key-bearing result buffers are zeroed in WASM memory before being freed."""
    spy = MemorySpy(wasm.memory)
    original = wasm.memory
    wasm.memory = spy  # type: ignore[assignment]
    try:
        key = wasm.make_private_key()
    finally:
        wasm.memory = original
    assert len(key) > 0
    assert len(key) in spy.zero_writes, "result buffer carrying the key must be zeroed"


# ── concurrency ───────────────────────────────────────────────────────────────


def test_concurrent_calls_are_serialised(wasm: Client) -> None:
    """Concurrent public calls all succeed on the shared single instance."""
    errors: list[Exception] = []
    keys: list[bytes] = []
    lock = threading.Lock()

    def worker() -> None:
        try:
            for _ in range(5):
                key = wasm.make_private_key()
                addr = wasm.pubkey_to_pubkeyhash_address(
                    wasm.public_key_from_private_key(key), Network.MAINNET
                )
                assert addr
                with lock:
                    keys.append(key)
        except Exception as exc:  # pragma: no cover - only on failure
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(keys) == 20
    assert len(set(keys)) == 20


# ── host-created Uint8Array scratch buffers ───────────────────────────────────


def test_cached_rng_scratch_buffer_survives_across_calls() -> None:
    """The RNG scratch Uint8Array is cached by the module and never freed host-side.

    The wasm module creates its RNG scratch ``Uint8Array`` once (via the
    ``__wbg_new_with_length`` host callback) and caches it in an externref
    table slot, reusing it for every keygen/signing call — mirroring the JS
    glue where ``new Uint8Array(n)`` is GC-managed, not call-scoped.

    Freeing that backing store at the end of a call would therefore be a
    use-after-free: the next keygen writes through the cached reference into
    freed memory and corrupts the allocator free-list (observed as
    ``memory fault``/``unreachable`` traps on subsequent unrelated calls,
    e.g. ``encode_multisig_challenge``). The host deliberately keeps
    ``_new_with_length`` free of any cleanup — see the NOTE in
    ``mintlayer/wasm/host.py``.

    Asserts two invariants:

    * no host-side free ever targets a (ptr, length) still referenced from
      the externref table, and
    * the SAME cached scratch buffer (ptr, length) is reused across two
      consecutive keygen calls, proving the module caches it — and thus why
      host-side freeing is forbidden.
    """
    from mintlayer.wasm.host import Uint8ArrayRef

    c = Client()
    try:
        freed: list[tuple[int, int]] = []
        original_free = c._free_wasm

        def spy_free(ptr: int, size: int, align: int = 1) -> None:
            freed.append((ptr, size))
            original_free(ptr, size, align)

        c._free_wasm = spy_free  # type: ignore[method-assign]

        def cached_refs() -> set[tuple[int, int]]:
            refs: set[tuple[int, int]] = set()
            for idx in range(c.table.size(c.store)):
                value = c.table.get(c.store, idx)
                if isinstance(value, Uint8ArrayRef):
                    refs.add((value.ptr, value.length))
            return refs

        c.make_private_key()
        cached_first = cached_refs()
        assert cached_first, "expected the module to cache its RNG scratch Uint8Array"

        c.make_private_key()
        cached_second = cached_refs()

        reused = cached_first & cached_second
        assert reused, (
            "the cached RNG scratch Uint8Array (same ptr, length) must survive and "
            "be reused across consecutive keygen calls — proving module-side "
            "caching, which is why host-side freeing would be a use-after-free"
        )
        still_referenced = cached_second & set(freed)
        assert not still_referenced, (
            "use-after-free: host-side free touched buffer(s) still referenced "
            f"by the externref table: {sorted(still_referenced)}"
        )
    finally:
        c.close()
