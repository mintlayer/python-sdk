"""Object ID derivation (mirrors go-sdk/wasm/ids.go)."""

from __future__ import annotations

from ._core import _WasmCore
from ._util import synchronized
from .types import Network


class IdsMixin(_WasmCore):
    @synchronized
    def get_pool_id(self, inputs: bytes, network: Network) -> str:
        """Return the pool ID derived from a transaction's inputs."""
        ptr, length = self._write_bytes(inputs)
        return self._call_return_string("get_pool_id", ptr, length, int(network))

    @synchronized
    def get_token_id(self, inputs: bytes, current_block_height: int, network: Network) -> str:
        """Return the fungible or NFT token ID derived from a transaction's inputs.

        ``current_block_height`` selects the token ID scheme for the active
        network upgrade.
        """
        ptr, length = self._write_bytes(inputs)
        return self._call_return_string(
            "get_token_id", ptr, length, current_block_height, int(network)
        )

    @synchronized
    def get_delegation_id(self, inputs: bytes, network: Network) -> str:
        """Return the delegation ID derived from a transaction's inputs."""
        ptr, length = self._write_bytes(inputs)
        return self._call_return_string("get_delegation_id", ptr, length, int(network))

    @synchronized
    def get_order_id(self, inputs: bytes, network: Network) -> str:
        """Return the DEX order ID derived from a transaction's inputs."""
        ptr, length = self._write_bytes(inputs)
        return self._call_return_string("get_order_id", ptr, length, int(network))
