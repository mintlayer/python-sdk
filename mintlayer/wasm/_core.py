"""Core WASM machinery shared by all method mixins.

:class:`~mintlayer.wasm.client.Client` combines this core with the per-area
method mixins (keys, addresses, transactions, ...).

Memory ownership protocol (verified against the wasm-bindgen JS glue that
ships with the vendored binary — see the ``web-gui`` repository's
``app/wasm-wrappers`` for the byte-identical build):

* **Plain inputs** (``_write_string``/``_write_bytes``): the WASM callee takes
  ownership (Rust ``String``/``Vec<u8>`` parameters) and frees them when the
  call returns. The glue never frees them host-side; neither must we — a
  host-side free is a double free that corrupts the allocator.
* **String-array arguments** (``_write_string_array``): the callee owns the
  table slots and the index array; the host releases nothing after the call.
  Only a pre-call write failure is rolled back.
* **Byte-array-array arguments** (``_write_uint8_array_array``): the callee
  owns the table slots and the index array, but the per-slice backing buffers
  are host-malloc'd and only copied (``to_vec``) — the host frees the backing
  buffers after the call (see ``intent.py``).
* **Result buffers**: host-owned; read, zeroed and freed by the
  ``_call_return_*`` helpers.

Treat the process memory of a long-lived ``Client`` as sensitive: key
material passes through WASM linear memory.
"""

from __future__ import annotations

import contextlib
import hashlib
import threading
from pathlib import Path
from typing import Any

from wasmtime import Engine, Instance, Linker, Memory, Module, Store, Table

from .types import Amount, WasmError

_WASM_PATH = Path(__file__).parent / "wasm_wrappers_bg.wasm"


def _load_and_verify_wasm() -> bytes:
    """Load the vendored WASM binary, failing closed if it misses its pin.

    The read and verification live in this single function so that any
    packaging mistake raises a descriptive :class:`WasmError` — at import
    time, which is intentional: a broken install must fail fast, not at
    first use deep inside a wallet operation.
    """
    if not _WASM_PATH.is_file():
        raise WasmError(f"mintlayer: WASM binary missing: {_WASM_PATH}")
    wasm_bytes = _WASM_PATH.read_bytes()
    pin_path = _WASM_PATH.with_suffix(".wasm.sha256")
    try:
        pin = pin_path.read_text().split()
    except FileNotFoundError as exc:
        raise WasmError(f"mintlayer: WASM integrity pin file missing: {pin_path}") from exc
    if not pin:
        raise WasmError(f"mintlayer: WASM integrity pin file is empty: {pin_path}")
    expected = pin[0].strip()
    actual = hashlib.sha256(wasm_bytes).hexdigest()
    if actual != expected:
        raise WasmError(
            f"mintlayer: WASM binary integrity check failed "
            f"(expected sha256 {expected}, got {actual})"
        )
    return wasm_bytes


_WASM_BYTES = _load_and_verify_wasm()


class _CallState:
    """Per-call side channel populated by host functions."""

    __slots__ = ("err_msg", "last_json")

    def __init__(self) -> None:
        self.err_msg: str = ""
        self.last_json: bytearray | None = None

    def reset(self) -> None:
        self.err_msg = ""
        self.last_json = None


class _WasmCore:
    """Core WASM machinery: lifecycle, call conventions and memory helpers."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.call_state = _CallState()
        self._last_err_msg = ""
        self._last_json: bytearray | None = None

        engine = Engine()
        self._engine = engine
        self.store = Store(engine)
        self._module = Module(engine, _WASM_BYTES)
        linker = Linker(engine)

        from .host import register_host_functions

        register_host_functions(self, linker)

        instance = linker.instantiate(self.store, self._module)
        self._instance: Instance | None = instance

        raw_exports = instance.exports(self.store)
        exports = {name: raw_exports[name] for name in raw_exports}
        self._exports = exports
        memory = exports.get("memory")
        if not isinstance(memory, Memory):
            raise WasmError("mintlayer: memory export not found")
        self.memory: Memory = memory
        table = exports.get("__wbindgen_externrefs")
        if not isinstance(table, Table):
            raise WasmError("mintlayer: __wbindgen_externrefs table not found")
        self.table: Table = table

    # ── lifecycle ────────────────────────────────────────────────────────────

    def close(self) -> None:
        """Release WASM resources. Subsequent calls raise."""
        with self.lock:
            self._instance = None
            self._exports = {}
            self.memory = None  # type: ignore[assignment]
            self.table = None  # type: ignore[assignment]

    def __enter__(self) -> _WasmCore:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ── export lookup ────────────────────────────────────────────────────────

    def get_export(self, name: str) -> Any:
        return self._exports.get(name)

    def _fn(self, name: str) -> Any:
        fn = self._exports.get(name)
        if fn is None:
            if self._instance is None:
                raise WasmError("mintlayer: client is closed")
            raise WasmError(f'mintlayer: function "{name}" not found')
        return fn

    # ── low-level call ───────────────────────────────────────────────────────

    def _call(self, name: str, *params: Any) -> list:
        """Execute a WASM export and return the raw results."""
        self._last_err_msg = ""
        self._last_json = None
        self.call_state.reset()
        fn = self._fn(name)
        try:
            res = fn(self.store, *params)
        except Exception as exc:
            # WasmThrow (from the host's __wbindgen_throw) and traps land here.
            # The cause chain is preserved: wasmtime trap traces are noisy but
            # invaluable for diagnosing memory/ABI failures.
            if self.call_state.err_msg:
                raise WasmError(f"mintlayer: {self.call_state.err_msg}") from exc
            raise WasmError(f"mintlayer: call {name}: {exc}") from exc
        self._last_err_msg = self.call_state.err_msg
        self._last_json = self.call_state.last_json
        # Func.__call__ returns None / scalar / list depending on result count.
        if res is None:
            return []
        if not isinstance(res, list):
            return [res]
        return res

    def _extract_error(self, err_idx: int) -> WasmError:
        if self._last_err_msg:
            return WasmError(f"mintlayer: {self._last_err_msg}")
        return WasmError(f"mintlayer: wasm returned error (ref={err_idx})")

    # ── call-return conventions ──────────────────────────────────────────────

    def _call_return_bytes(self, name: str, *params: Any) -> bytes:
        """fn expects [ptr, len, errRef, errFlag]."""
        ret = self._call(name, *params)
        if len(ret) >= 4 and ret[3] != 0:
            # No buffer cleanup on the error path, matching the reference
            # glue: it zeroes the pointer instead of freeing, because ret[0]
            # is not a valid allocation once the error flag is set (the Rust
            # Err variant allocates no result) - freeing it could corrupt
            # the allocator.
            raise self._extract_error(ret[2])
        if len(ret) < 2:
            raise WasmError(f"mintlayer: unexpected return count from {name}")
        ptr, length = ret[0], ret[1]
        data = self._read_bytes(ptr, length) if length else bytearray()
        if data is None:
            raise WasmError("mintlayer: memory read failed")
        with contextlib.suppress(Exception):
            self.memory.write(self.store, b"\x00" * length, ptr)
        self._free_wasm(ptr, length)
        return bytes(data)

    def _call_return_bytes_no_err(self, name: str, *params: Any) -> bytes:
        """fn expects [ptr, len] (infallible)."""
        ret = self._call(name, *params)
        if len(ret) < 2:
            raise WasmError(f"mintlayer: unexpected return count from {name}")
        ptr, length = ret[0], ret[1]
        data = self._read_bytes(ptr, length) if length else bytearray()
        if data is None:
            raise WasmError("mintlayer: memory read failed")
        with contextlib.suppress(Exception):
            self.memory.write(self.store, b"\x00" * length, ptr)
        self._free_wasm(ptr, length)
        return bytes(data)

    def _call_return_string(self, name: str, *params: Any) -> str:
        """fn expects [ptr, len, errRef, errFlag]; result is UTF-8."""
        ret = self._call(name, *params)
        if len(ret) >= 4 and ret[3] != 0:
            # Error-path buffers are not freed: see _call_return_bytes.
            raise self._extract_error(ret[2])
        if len(ret) < 2:
            raise WasmError(f"mintlayer: unexpected return count from {name}")
        ptr, length = ret[0], ret[1]
        data = self._read_bytes(ptr, length)
        if data is None:
            raise WasmError("mintlayer: memory read failed")
        with contextlib.suppress(Exception):
            self.memory.write(self.store, b"\x00" * length, ptr)
        self._free_wasm(ptr, length)
        return bytes(data).decode("utf-8")

    def _call_return_bool(self, name: str, *params: Any) -> bool:
        """fn expects [bool, errRef, errFlag]."""
        ret = self._call(name, *params)
        if len(ret) >= 3 and ret[2] != 0:
            raise self._extract_error(ret[1])
        if len(ret) < 1:
            raise WasmError(f"mintlayer: unexpected return count from {name}")
        return ret[0] != 0

    def _call_return_u32(self, name: str, *params: Any) -> int:
        """fn expects [u32, errRef, errFlag]."""
        ret = self._call(name, *params)
        if len(ret) >= 3 and ret[2] != 0:
            raise self._extract_error(ret[1])
        if len(ret) < 1:
            raise WasmError(f"mintlayer: unexpected return count from {name}")
        return ret[0] & 0xFFFFFFFF

    def _call_return_u64(self, name: str, *params: Any) -> int:
        """fn expects [u64, errRef, errFlag]."""
        ret = self._call(name, *params)
        if len(ret) >= 3 and ret[2] != 0:
            raise self._extract_error(ret[1])
        if len(ret) < 1:
            raise WasmError(f"mintlayer: unexpected return count from {name}")
        return ret[0] & 0xFFFFFFFFFFFFFFFF

    def _call_return_amount(self, name: str, *params: Any) -> Amount:
        """fn returns a single Amount pointer (infallible)."""
        ret = self._call(name, *params)
        if len(ret) == 0:
            raise WasmError(f"mintlayer: no return value from {name}")
        return self._read_amount(ret[0])

    def _call_return_amount_fallible(self, name: str, *params: Any) -> Amount:
        """fn expects [amtPtr, errRef, errFlag]."""
        ret = self._call(name, *params)
        if len(ret) >= 3 and ret[2] != 0:
            raise self._extract_error(ret[1])
        if len(ret) == 0:
            raise WasmError(f"mintlayer: no return value from {name}")
        return self._read_amount(ret[0])

    def _call_void_fallible(self, name: str, *params: Any) -> None:
        """fn expects [errRef, errFlag] (void on success)."""
        ret = self._call(name, *params)
        if len(ret) >= 2 and ret[1] != 0:
            raise self._extract_error(ret[0])

    def _call_return_json(self, name: str, *params: Any) -> bytes:
        """fn returns a JSON object captured by the host's JSON.parse."""
        ret = self._call(name, *params)
        if len(ret) >= 3 and ret[2] != 0:
            raise self._extract_error(ret[1])
        if self._last_json is not None:
            return bytes(self._last_json)
        raise WasmError(f"mintlayer: no JSON result from {name}")

    # ── memory helpers ───────────────────────────────────────────────────────

    def _read_bytes(self, ptr: int, length: int) -> bytearray | None:
        return self.memory.read(self.store, ptr, ptr + length)

    def _write_bytes(self, data: bytes) -> tuple[int, int]:
        """Copy ``data`` into WASM heap; returns (ptr, len).

        The buffer becomes callee-owned: the WASM function takes the bytes by
        value and frees them when it returns. Do NOT free host-side — that is
        a double free. (``amount_from_atoms`` is likewise callee-owned; the
        error path in :meth:`_new_wasm_amount` frees only because ownership
        was never transferred.)
        """
        if not data:
            return 0, 0
        ptr = self._invoke1("__wbindgen_malloc", len(data), 1)
        if self.memory.write(self.store, data, ptr) is None:
            raise WasmError("mintlayer: memory write failed")
        return ptr, len(data)

    def _write_string(self, s: str) -> tuple[int, int]:
        return self._write_bytes(s.encode("utf-8"))

    def _free_wasm(self, ptr: int, size: int, align: int = 1) -> None:
        """Free a host-owned WASM allocation.

        Failures are deliberately swallowed: a cleanup error must not mask
        the call's outcome, and if the allocator is genuinely corrupted the
        NEXT wasm call traps loudly anyway (surfaces as WasmError).
        """
        if ptr == 0:
            return
        with contextlib.suppress(Exception):
            self._fn("__wbindgen_free")(self.store, ptr, size, align)

    def _write_optional_string(self, s: str | None) -> tuple[int, int]:
        if s is None:
            return 0, 0
        return self._write_string(s)

    def _write_optional_bytes(self, b: bytes | None) -> tuple[int, int]:
        if b is None:
            return 0, 0
        return self._write_bytes(b)

    def _new_wasm_amount(self, amount: Amount) -> int:
        """Allocate an Amount in the WASM heap and return its handle.

        ``amount_from_atoms`` takes ownership of the string allocation, so the
        string is NOT freed here.
        """
        str_ptr, str_len = self._write_string(amount.atoms)
        try:
            return self._invoke1("amount_from_atoms", str_ptr, str_len)
        except WasmError:
            self._free_wasm(str_ptr, str_len)
            raise

    def _read_amount(self, wasm_ptr: int) -> Amount:
        """Read the atom string from a WASM Amount handle (consumes it).

        Deliberately uses ``_call_export`` rather than ``_call`` (mirrors
        go-sdk's readAmount): ``amount_atoms`` decodes after the parent call
        already extracted its error state, and routing it through ``_call``
        would reset the per-call ``err_msg``/``last_json`` the parent
        captured.
        """
        ret = self._call_export("amount_atoms", wasm_ptr)
        if len(ret) < 2:
            raise WasmError("mintlayer: amount_atoms failed")
        ptr, length = ret[0], ret[1]
        data = self._read_bytes(ptr, length)
        if data is None:
            raise WasmError("mintlayer: memory read for amount failed")
        atoms = data.decode("utf-8")
        self._free_wasm(ptr, length)
        return Amount.from_atoms(atoms)

    # ── externref-index arrays (passArrayJsValueToWasm0 pattern) ─────────────
    #
    # Ownership: during the call the WASM callee takes ownership of the index
    # array, the externref table slots, and (for Uint8Array entries) reads and
    # copies the backing buffers. The callee itself releases the index array
    # and deallocs the table slots, so the host must never re-read the array
    # or dealloc the slots after the call — doing so double-frees free-list
    # entries and corrupts later allocations ("array contains a value of the
    # wrong type" on subsequent multi-element calls). The Uint8Array backing
    # buffers, however, are malloc'd host-side and only copied by the callee
    # (to_vec): the host frees those after the call.
    #
    # Known wasm-bindgen trait: a FAILING array call leaks a few slots (the
    # callee's error path skips part of its cleanup). Not soundly fixable
    # host-side — never "compensate" by dealloc'ing, which is worse.

    def _write_string_array(self, strs: list[str]) -> tuple[int, list[int]]:
        """Write ``[string]`` as an array of externref table indices.

        Returns (array_ptr, table_indices). The index array and the slots
        become callee-owned once the call is made — never call
        :meth:`_dealloc_indices` on them afterwards (only pre-call rollback,
        which this method already handles internally).
        """
        indices: list[int] = []
        if not strs:
            return 0, indices
        arr_ptr = self._malloc_array(len(strs))
        try:
            for i, s in enumerate(strs):
                idx = self._invoke1("__externref_table_alloc")
                indices.append(idx)
                self.table.set(self.store, idx, s)
                if (
                    self.memory.write(self.store, idx.to_bytes(4, "little"), arr_ptr + i * 4)
                    is None
                ):
                    raise WasmError("mintlayer: memory write failed")
        except BaseException:
            self._dealloc_indices(indices)
            with contextlib.suppress(Exception):
                self._fn("__wbindgen_free")(self.store, arr_ptr, len(strs) * 4, 4)
            raise
        return arr_ptr, indices

    def _write_uint8_array_array(
        self, slices: list[bytes]
    ) -> tuple[int, list[int], list[tuple[int, int]]]:
        """Write ``[bytes]`` as an array of externref table indices.

        Each slice is copied into WASM heap and wrapped as a Uint8Array.
        Returns (array_ptr, table_indices, backing_buffers). After the call:
        the table slots and the index array are CALLEE-OWNED — never dealloc
        them (doing so corrupts the table free list, observed as
        ``unreachable`` traps on subsequent calls). The backing buffers,
        however, are malloc'd host-side and only copied by the callee
        (``to_vec``): the host frees those after the call (see
        ``intent.encode_signed_transaction_intent``).
        """
        from .host import Uint8ArrayRef

        indices: list[int] = []
        buffers: list[tuple[int, int]] = []
        if not slices:
            return 0, indices, buffers
        arr_ptr = self._malloc_array(len(slices))
        try:
            for i, b in enumerate(slices):
                wasm_ptr, wasm_len = self._write_bytes(b)
                buffers.append((wasm_ptr, wasm_len))
                idx = self._invoke1("__externref_table_alloc")
                indices.append(idx)
                self.table.set(self.store, idx, Uint8ArrayRef(wasm_ptr, wasm_len))
                if (
                    self.memory.write(self.store, idx.to_bytes(4, "little"), arr_ptr + i * 4)
                    is None
                ):
                    raise WasmError("mintlayer: memory write failed")
        except BaseException:
            self._dealloc_indices(indices)
            for ptr, length in buffers:
                self._free_wasm(ptr, length)
            with contextlib.suppress(Exception):
                self._fn("__wbindgen_free")(self.store, arr_ptr, len(slices) * 4, 4)
            raise
        return arr_ptr, indices, buffers

    def _malloc_array(self, count: int) -> int:
        return self._invoke1("__wbindgen_malloc", count * 4, 4)

    def _call_export(self, name: str, *params: Any) -> list:
        """Call a WASM export, normalising the result to a list."""
        res = self._fn(name)(self.store, *params)
        if res is None:
            return []
        if not isinstance(res, list):
            return [res]
        return res

    def _invoke1(self, name: str, *params: Any) -> int:
        """Call a WASM export returning exactly one i32/i64 result."""
        ret = self._call_export(name, *params)
        if len(ret) != 1:
            raise WasmError(f"mintlayer: {name} returned {len(ret)} results")
        return ret[0]

    def _dealloc_indices(self, indices: list[int]) -> None:
        """Release externref table slots.

        ONLY for pre-call rollback (a write failed before the callee ever ran).
        After a call, the slots are callee-owned — deallocating them again
        corrupts the table free list.
        """
        if not indices:
            return
        dealloc = self.get_export("__externref_table_dealloc")
        if dealloc is None:
            return
        for idx in indices:
            with contextlib.suppress(Exception):
                dealloc(self.store, idx)
