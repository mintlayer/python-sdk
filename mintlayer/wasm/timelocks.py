"""Timelock encoding (mirrors go-sdk/wasm/timelocks.go)."""

from __future__ import annotations

from ._core import _WasmCore
from ._util import synchronized


class TimelocksMixin(_WasmCore):
    @synchronized
    def encode_lock_for_block_count(self, block_count: int) -> bytes:
        """Encode a "lock until N more blocks have passed" timelock."""
        return self._call_return_bytes_no_err("encode_lock_for_block_count", block_count)

    @synchronized
    def encode_lock_for_seconds(self, seconds: int) -> bytes:
        """Encode a "lock for N more seconds" timelock."""
        return self._call_return_bytes_no_err("encode_lock_for_seconds", seconds)

    @synchronized
    def encode_lock_until_height(self, block_height: int) -> bytes:
        """Encode a "lock until absolute block height" timelock."""
        return self._call_return_bytes_no_err("encode_lock_until_height", block_height)

    @synchronized
    def encode_lock_until_time(self, timestamp_seconds: int) -> bytes:
        """Encode a "lock until absolute UNIX timestamp" timelock."""
        return self._call_return_bytes_no_err("encode_lock_until_time", timestamp_seconds)
