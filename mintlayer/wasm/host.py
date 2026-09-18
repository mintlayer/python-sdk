"""Host module for the embedded WASM module.

The WASM binary imports all host functions from the module
``"./wasm_wrappers_bg.js"`` (the wasm-bindgen JS glue). This module implements
those 31 imports natively for wasmtime, mirroring go-sdk/wasm/host.go:

* random number generation (``os.urandom``) feeds key generation and signing,
* JSON round-tripping implements the tsify/serde ``TxAdditionalInfo`` path,
* error strings are captured per call via a side channel (``cast_...2`` /
  ``__wbindgen_throw``) instead of being read from the externref table.

Externref values are real Python objects; ``None`` represents the null/undefined
externref (registry handle 0 in the Go SDK).
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from wasmtime import Func, FuncType, Linker, ValType

if TYPE_CHECKING:
    from ._core import _WasmCore

HOST_MODULE = "./wasm_wrappers_bg.js"

_I32 = ValType.i32()
_ANYREF = ValType.externref()


class _GlobalSentinel:
    """Represents JavaScript ``globalThis``."""


class _CryptoSentinel:
    """Represents the ``crypto`` object on globalThis."""


class Uint8ArrayRef:
    """A JS Uint8Array whose backing store lives in WASM linear memory."""

    __slots__ = ("ptr", "length")

    def __init__(self, ptr: int, length: int) -> None:
        self.ptr = ptr
        self.length = length


class FunctionSentinel:
    """A JS function created via ``new Function(code)``."""

    __slots__ = ("code",)

    def __init__(self, code: str) -> None:
        self.code = code


GLOBAL = _GlobalSentinel()
CRYPTO = _CryptoSentinel()


class WasmThrow(Exception):
    """Raised by ``__wbindgen_throw`` to abort the current WASM invocation."""


def _json_dumps(value: Any) -> str:
    """Serialise a host value to JSON, honouring SDK types (serde shape)."""
    if hasattr(value, "to_json_value"):
        value = value.to_json_value()
    return json.dumps(value, separators=(",", ":"))


def register_host_functions(client: _WasmCore, linker: Linker) -> None:
    """Define the 31 host imports on ``linker`` for ``client``'s store."""
    store = client.store
    state = client.call_state

    def invoke(fn_name: str, *args: Any) -> list:
        """Call a WASM export from within a host function; results as list."""
        fn = client.get_export(fn_name)
        if fn is None:
            raise WasmThrow(f"{fn_name} not found")
        res = fn(store, *args)
        if res is None:
            return []
        if not isinstance(res, list):
            return [res]
        return res

    def alloc_table_slot(value: Any) -> int:
        """Allocate an externref-table slot, store ``value`` in it, return the index."""
        idx = invoke("__externref_table_alloc")[0]
        client.table.set(store, idx, value)
        return idx

    def signal_exception(msg: str) -> None:
        """Mirror JS ``handleError``: stash the exception so WASM returns Err.

        The message is recorded in the per-call side channel so host-side
        failures surface even if the WASM error path never calls
        ``__wbindgen_cast_...2`` (a later cast still overwrites it with the
        richer Rust-side message).

        ``__wbindgen_exn_store`` receives the externref holding the exception
        value (JS stores the ``Error`` object); we store the message string so
        the WASM unwind path reads this call's payload instead of a stale slot.

        Like the JS glue and go-sdk's host, the host function itself returns
        normally after stashing — whether the callee converts the stored
        exception into an Err is decided by the module's generated code
        (wasm-bindgen contract); the host cannot force an Err return.
        """
        if not state.err_msg:
            state.err_msg = msg
        if client.get_export("__wbindgen_exn_store") is None:
            return
        invoke("__wbindgen_exn_store", alloc_table_slot(msg))

    def write_string_to_mem(out_ptr: int, s: str) -> None:
        """Write (ptr, len) of ``s`` as two LE u32s at ``out_ptr``."""
        zeros = (0).to_bytes(4, "little")
        data = s.encode()
        if not data:
            client.memory.write(store, zeros, out_ptr)
            client.memory.write(store, zeros, out_ptr + 4)
            return
        ptr = invoke("__wbindgen_malloc", len(data), 1)[0]
        client.memory.write(store, data, ptr)
        client.memory.write(store, ptr.to_bytes(4, "little"), out_ptr)
        client.memory.write(store, len(data).to_bytes(4, "little"), out_ptr + 4)

    def fill_random(buf: Any) -> None:
        if not isinstance(buf, Uint8ArrayRef):
            signal_exception("fillRandom: expected Uint8Array")
            return
        data = os.urandom(buf.length)
        # A failed write must never pass silently: the WASM side would proceed
        # with stale/zero bytes as key material.
        if client.memory.write(store, data, buf.ptr) is None:
            signal_exception("fillRandom: memory write failed")

    def debug_string(value: Any) -> str:
        if value is None:
            return "undefined"
        if isinstance(value, str):
            return json.dumps(value)
        if isinstance(value, Uint8ArrayRef):
            return f"Uint8Array({value.length})"
        if isinstance(value, _GlobalSentinel):
            return "[object global]"
        if isinstance(value, _CryptoSentinel):
            return "[object Crypto]"
        if isinstance(value, FunctionSentinel):
            return f"function {value.code}"
        return _json_dumps(value)

    def def_func(name: str, params: list, results: list, func: Any) -> None:
        linker.define(store, HOST_MODULE, name, Func(store, FuncType(params, results), func))

    # ── global accessors: () -> i32 (externref table index) ──────────────────
    def _global_accessor() -> int:
        return alloc_table_slot(GLOBAL)

    def _null_accessor() -> int:
        return 0

    def_func("__wbg_static_accessor_GLOBAL_12837167ad935116", [], [_I32], _global_accessor)
    def_func("__wbg_static_accessor_GLOBAL_THIS_e628e89ab3b1c95f", [], [_I32], _global_accessor)
    def_func("__wbg_static_accessor_SELF_a621d3dfbb60d0ce", [], [_I32], _null_accessor)
    def_func("__wbg_static_accessor_WINDOW_f8727f0cf888e0bd", [], [_I32], _null_accessor)

    # ── crypto property access: (anyref) -> anyref ───────────────────────────
    def _crypto(value: Any) -> Any:
        if isinstance(value, _GlobalSentinel):
            return CRYPTO
        return None

    def _null_value(value: Any) -> Any:
        return None

    def_func("__wbg_crypto_86f2631e91b51511", [_ANYREF], [_ANYREF], _crypto)
    def_func("__wbg_msCrypto_d562bbe83e0d4b91", [_ANYREF], [_ANYREF], _null_value)
    def_func("__wbg_process_3975fd6c72f520aa", [_ANYREF], [_ANYREF], _null_value)
    def_func("__wbg_node_e1f24f89a7336c2e", [_ANYREF], [_ANYREF], _null_value)
    def_func("__wbg_versions_4e31226f5e8dc909", [_ANYREF], [_ANYREF], _null_value)

    # ── RNG: (anyref, anyref) -> () ──────────────────────────────────────────
    def_func(
        "__wbg_getRandomValues_b3f15fcbfabb0f8b",
        [_ANYREF, _ANYREF],
        [],
        lambda _obj, buf: fill_random(buf),
    )
    def_func(
        "__wbg_randomFillSync_f8c153b79f285817",
        [_ANYREF, _ANYREF],
        [],
        lambda _obj, buf: fill_random(buf),
    )

    # ── require: () -> anyref (null so WASM skips the Node.js crypto path) ───
    def_func("__wbg_require_b74f47fc2d022fd6", [], [_ANYREF], lambda: None)

    # ── function call stubs ──────────────────────────────────────────────────
    def _call2(fn: Any, _this: Any) -> Any:
        if isinstance(fn, FunctionSentinel) and fn.code == "return this":
            return GLOBAL
        signal_exception("unsupported call/2")
        return None

    def _call3(_fn: Any, _this: Any, _arg: Any) -> Any:
        signal_exception("unsupported call (one arg)")
        return None

    def_func("__wbg_call_389efe28435a9388", [_ANYREF, _ANYREF], [_ANYREF], _call2)
    def_func("__wbg_call_4708e0c13bdc8e95", [_ANYREF, _ANYREF, _ANYREF], [_ANYREF], _call3)

    # ── Uint8Array operations ────────────────────────────────────────────────
    def _length(value: Any) -> int:
        if isinstance(value, Uint8ArrayRef):
            return value.length
        return 0

    def _new_with_length(size: int) -> Any:
        # NOTE: the backing store is deliberately NOT freed host-side. The WASM
        # module treats these Uint8Arrays as GC-managed JS values: it caches
        # them in externref table slots (e.g. the RNG scratch buffer) and
        # reuses them across calls. Freeing on call end would be a use-after-
        # free; the cost is a bounded, one-time allocation per cached buffer.
        ptr = invoke("__wbindgen_malloc", size, 1)[0]
        if client.memory.write(store, b"\x00" * size, ptr) is None:
            signal_exception("new Uint8Array: memory write failed")
            return None
        return Uint8ArrayRef(ptr, size)

    def _prototypesetcall(dst_ptr: int, dst_len: int, src: Any) -> None:
        if isinstance(src, Uint8ArrayRef):
            n = min(src.length, dst_len)
            data = client.memory.read(store, src.ptr, src.ptr + n)
            if data:
                client.memory.write(store, data, dst_ptr)

    def _subarray(value: Any, start: int, end: int) -> Any:
        # JS spec: TypedArray.prototype.subarray clamps the range silently.
        # (Divergence: JS also accepts negative indices as from-the-end; this
        # host clamps them to 0 — wasm-bindgen only ever passes u32 offsets.)
        if isinstance(value, Uint8ArrayRef):
            start = max(0, min(start, value.length))
            end = max(start, min(end, value.length))
            return Uint8ArrayRef(value.ptr + start, end - start)
        return None

    def_func("__wbg_length_32ed9a279acd054c", [_ANYREF], [_I32], _length)
    def_func("__wbg_new_with_length_a2c39cbe88fd8ff1", [_I32], [_ANYREF], _new_with_length)
    def_func(
        "__wbg_prototypesetcall_bdcdcc5842e4d77d", [_I32, _I32, _ANYREF], [], _prototypesetcall
    )
    def_func("__wbg_subarray_a96e1fef17ed23cb", [_ANYREF, _I32, _I32], [_ANYREF], _subarray)

    # ── JSON: JSON.parse captures the raw bytes for decode_*_to_js results ───
    def _parse(ptr: int, length: int) -> Any:
        data = client.memory.read(store, ptr, ptr + length)
        if data is None:
            signal_exception("JSON.parse: memory read failed")
            return None
        try:
            value = json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            signal_exception(f"JSON.parse: {exc}")
            return None
        state.last_json = data
        return value

    def _stringify(value: Any) -> Any:
        if value is None:
            signal_exception("JSON.stringify: unknown reference")
            return None
        try:
            return _json_dumps(value)
        except (TypeError, ValueError) as exc:
            signal_exception(f"JSON.stringify: {exc}")
            return None

    def_func("__wbg_parse_708461a1feddfb38", [_I32, _I32], [_ANYREF], _parse)
    def_func("__wbg_stringify_8d1cc6ff383e8bae", [_ANYREF], [_ANYREF], _stringify)

    # ── new Function(code): (i32, i32) -> anyref ─────────────────────────────
    def _new_no_args(ptr: int, length: int) -> Any:
        data = client.memory.read(store, ptr, ptr + length)
        return FunctionSentinel(data.decode("utf-8", errors="replace") if data else "")

    def_func("__wbg_new_no_args_1c7c842f08d00ebb", [_I32, _I32], [_ANYREF], _new_no_args)

    # ── cast intrinsics: (i32, i32) -> anyref ────────────────────────────────
    def _cast_uint8array(ptr: int, length: int) -> Any:
        return Uint8ArrayRef(ptr, length)

    def _cast_string(ptr: int, length: int) -> Any:
        data = client.memory.read(store, ptr, ptr + length)
        s = data.decode("utf-8", errors="replace") if data else ""
        # Rust errors cross here as their Display string; capture for the caller.
        state.err_msg = s
        return s

    def_func("__wbindgen_cast_0000000000000001", [_I32, _I32], [_ANYREF], _cast_uint8array)
    def_func("__wbindgen_cast_0000000000000002", [_I32, _I32], [_ANYREF], _cast_string)

    # ── debug / type predicates: (anyref) -> i32 ─────────────────────────────
    def _debug_string(out_ptr: int, value: Any) -> None:
        write_string_to_mem(out_ptr, debug_string(value))

    def _is_function(value: Any) -> int:
        return 1 if isinstance(value, FunctionSentinel) else 0

    def _is_object(value: Any) -> int:
        return 1 if isinstance(value, (_GlobalSentinel, _CryptoSentinel, Uint8ArrayRef)) else 0

    def _is_string(value: Any) -> int:
        return 1 if isinstance(value, str) else 0

    def _is_undefined(value: Any) -> int:
        return 1 if value is None else 0

    def_func("__wbg___wbindgen_debug_string_0bc8482c6e3508ae", [_I32, _ANYREF], [], _debug_string)
    def_func("__wbg___wbindgen_is_function_0095a73b8b156f76", [_ANYREF], [_I32], _is_function)
    def_func("__wbg___wbindgen_is_object_5ae8e5880f2c1fbd", [_ANYREF], [_I32], _is_object)
    def_func("__wbg___wbindgen_is_string_cd444516edc5b180", [_ANYREF], [_I32], _is_string)
    def_func("__wbg___wbindgen_is_undefined_9e4d92534c42d778", [_ANYREF], [_I32], _is_undefined)

    # ── string_get: (i32, anyref) -> () ──────────────────────────────────────
    def _string_get(out_ptr: int, value: Any) -> None:
        if isinstance(value, str):
            write_string_to_mem(out_ptr, value)
            return
        client.memory.write(store, (0).to_bytes(4, "little"), out_ptr)
        client.memory.write(store, (0).to_bytes(4, "little"), out_ptr + 4)

    def_func("__wbg___wbindgen_string_get_72fb696202c56729", [_I32, _ANYREF], [], _string_get)

    # ── throw: (i32, i32) -> () — aborts the WASM invocation ─────────────────
    def _throw(ptr: int, length: int) -> None:
        data = client.memory.read(store, ptr, ptr + length)
        msg = data.decode("utf-8", errors="replace") if data else ""
        state.err_msg = msg
        raise WasmThrow(f"wasm throw: {msg}")

    def_func("__wbg___wbindgen_throw_be289d5034ed271b", [_I32, _I32], [], _throw)

    # ── externref table init: () -> () ───────────────────────────────────────
    def _init_externref_table() -> None:
        for _ in range(4):
            invoke("__externref_table_alloc")

    def_func("__wbindgen_init_externref_table", [], [], _init_externref_table)
