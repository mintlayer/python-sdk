"""Address encoding (mirrors go-sdk/wasm/addresses.go)."""

from __future__ import annotations

from ._core import _WasmCore
from ._util import synchronized
from .types import Network


class AddressesMixin(_WasmCore):
    @synchronized
    def encode_destination(self, address: str, network: Network) -> bytes:
        """Encode a bech32m address string into a binary destination."""
        ptr, length = self._write_string(address)
        return self._call_return_bytes("encode_destination", ptr, length, int(network))

    @synchronized
    def pubkey_to_pubkeyhash_address(self, pubkey: bytes, network: Network) -> str:
        """Derive a pay-to-public-key-hash bech32m address."""
        ptr, length = self._write_bytes(pubkey)
        return self._call_return_string("pubkey_to_pubkeyhash_address", ptr, length, int(network))

    @synchronized
    def encode_multisig_challenge(
        self, pubkeys: bytes, min_required_signatures: int, network: Network
    ) -> bytes:
        """Encode a multisig challenge (script) into binary.

        ``pubkeys`` is the concatenation of encoded public keys.
        """
        ptr, length = self._write_bytes(pubkeys)
        return self._call_return_bytes(
            "encode_multisig_challenge", ptr, length, min_required_signatures, int(network)
        )

    @synchronized
    def multisig_challenge_to_address(self, challenge: bytes, network: Network) -> str:
        """Convert a binary multisig challenge into its bech32m address."""
        ptr, length = self._write_bytes(challenge)
        return self._call_return_string("multisig_challenge_to_address", ptr, length, int(network))
