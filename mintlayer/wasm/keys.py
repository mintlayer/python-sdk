"""Key derivation (mirrors go-sdk/wasm/keys.go)."""

from __future__ import annotations

from ._core import _WasmCore
from ._util import synchronized
from .types import Network


class KeysMixin(_WasmCore):
    @synchronized
    def make_private_key(self) -> bytes:
        """Generate a new random private key."""
        return self._call_return_bytes_no_err("make_private_key")

    @synchronized
    def make_default_account_privkey(self, mnemonic: str, network: Network) -> bytes:
        """Derive the extended private key for the default account (account 0).

        Derivation path: 44'/mintlayer_coin_type'/0'
        """
        ptr, length = self._write_string(mnemonic)
        return self._call_return_bytes("make_default_account_privkey", ptr, length, int(network))

    @synchronized
    def public_key_from_private_key(self, privkey: bytes) -> bytes:
        """Derive the compressed public key for a private key."""
        ptr, length = self._write_bytes(privkey)
        return self._call_return_bytes("public_key_from_private_key", ptr, length)

    @synchronized
    def extended_public_key_from_extended_private_key(self, privkey: bytes) -> bytes:
        """Derive the extended public key from an extended private key."""
        ptr, length = self._write_bytes(privkey)
        return self._call_return_bytes("extended_public_key_from_extended_private_key", ptr, length)

    @synchronized
    def make_receiving_address(self, account_privkey: bytes, key_index: int) -> bytes:
        """Derive a receiving (external) address key at the given index."""
        ptr, length = self._write_bytes(account_privkey)
        return self._call_return_bytes("make_receiving_address", ptr, length, key_index)

    @synchronized
    def make_change_address(self, account_privkey: bytes, key_index: int) -> bytes:
        """Derive a change (internal) address key at the given index."""
        ptr, length = self._write_bytes(account_privkey)
        return self._call_return_bytes("make_change_address", ptr, length, key_index)

    @synchronized
    def make_receiving_address_public_key(self, account_pubkey: bytes, key_index: int) -> bytes:
        """Derive the receiving address public key from an extended public key."""
        ptr, length = self._write_bytes(account_pubkey)
        return self._call_return_bytes("make_receiving_address_public_key", ptr, length, key_index)

    @synchronized
    def make_change_address_public_key(self, account_pubkey: bytes, key_index: int) -> bytes:
        """Derive the change address public key from an extended public key."""
        ptr, length = self._write_bytes(account_pubkey)
        return self._call_return_bytes("make_change_address_public_key", ptr, length, key_index)
