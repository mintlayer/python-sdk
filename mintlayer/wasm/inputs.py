"""Transaction input encoding (mirrors go-sdk/wasm/inputs.go)."""

from __future__ import annotations

from ._core import _WasmCore
from ._util import synchronized
from .types import Amount, Network, TokenUnfreezable


class InputsMixin(_WasmCore):
    @synchronized
    def encode_input_for_utxo(self, outpoint_source_id: bytes, output_index: int) -> bytes:
        """Encode a UTXO input from an outpoint source ID and output index."""
        ptr, length = self._write_bytes(outpoint_source_id)
        return self._call_return_bytes("encode_input_for_utxo", ptr, length, output_index)

    @synchronized
    def encode_input_for_withdraw_from_delegation(
        self, delegation_id: str, amount: Amount, nonce: int, network: Network
    ) -> bytes:
        """Create an input that withdraws from a delegation."""
        id_ptr, id_len = self._write_string(delegation_id)
        amt_ptr = self._new_wasm_amount(amount)
        return self._call_return_bytes(
            "encode_input_for_withdraw_from_delegation",
            id_ptr,
            id_len,
            amt_ptr,
            nonce,
            int(network),
        )

    @synchronized
    def encode_input_for_mint_tokens(
        self, token_id: str, amount: Amount, nonce: int, network: Network
    ) -> bytes:
        """Create an input to mint tokens."""
        id_ptr, id_len = self._write_string(token_id)
        amt_ptr = self._new_wasm_amount(amount)
        return self._call_return_bytes(
            "encode_input_for_mint_tokens", id_ptr, id_len, amt_ptr, nonce, int(network)
        )

    @synchronized
    def encode_input_for_unmint_tokens(self, token_id: str, nonce: int, network: Network) -> bytes:
        """Create an input to unmint tokens."""
        id_ptr, id_len = self._write_string(token_id)
        return self._call_return_bytes(
            "encode_input_for_unmint_tokens", id_ptr, id_len, nonce, int(network)
        )

    @synchronized
    def encode_input_for_lock_token_supply(
        self, token_id: str, nonce: int, network: Network
    ) -> bytes:
        """Create an input to lock the token supply."""
        id_ptr, id_len = self._write_string(token_id)
        return self._call_return_bytes(
            "encode_input_for_lock_token_supply", id_ptr, id_len, nonce, int(network)
        )

    @synchronized
    def encode_input_for_freeze_token(
        self,
        token_id: str,
        is_token_unfreezable: TokenUnfreezable,
        nonce: int,
        network: Network,
    ) -> bytes:
        """Create an input to freeze a token."""
        id_ptr, id_len = self._write_string(token_id)
        return self._call_return_bytes(
            "encode_input_for_freeze_token",
            id_ptr,
            id_len,
            int(is_token_unfreezable),
            nonce,
            int(network),
        )

    @synchronized
    def encode_input_for_unfreeze_token(self, token_id: str, nonce: int, network: Network) -> bytes:
        """Create an input to unfreeze a token."""
        id_ptr, id_len = self._write_string(token_id)
        return self._call_return_bytes(
            "encode_input_for_unfreeze_token", id_ptr, id_len, nonce, int(network)
        )

    @synchronized
    def encode_input_for_change_token_authority(
        self, token_id: str, new_authority: str, nonce: int, network: Network
    ) -> bytes:
        """Create an input to change the token authority."""
        id_ptr, id_len = self._write_string(token_id)
        auth_ptr, auth_len = self._write_string(new_authority)
        return self._call_return_bytes(
            "encode_input_for_change_token_authority",
            id_ptr,
            id_len,
            auth_ptr,
            auth_len,
            nonce,
            int(network),
        )

    @synchronized
    def encode_input_for_change_token_metadata_uri(
        self, token_id: str, new_metadata_uri: str, nonce: int, network: Network
    ) -> bytes:
        """Create an input to change the token metadata URI."""
        id_ptr, id_len = self._write_string(token_id)
        uri_ptr, uri_len = self._write_string(new_metadata_uri)
        return self._call_return_bytes(
            "encode_input_for_change_token_metadata_uri",
            id_ptr,
            id_len,
            uri_ptr,
            uri_len,
            nonce,
            int(network),
        )

    @synchronized
    def encode_input_for_conclude_order(
        self, order_id: str, nonce: int, current_block_height: int, network: Network
    ) -> bytes:
        """Create an input that concludes an order."""
        id_ptr, id_len = self._write_string(order_id)
        return self._call_return_bytes(
            "encode_input_for_conclude_order",
            id_ptr,
            id_len,
            nonce,
            current_block_height,
            int(network),
        )

    @synchronized
    def encode_input_for_fill_order(
        self,
        order_id: str,
        fill_amount: Amount,
        destination: str,
        nonce: int,
        current_block_height: int,
        network: Network,
    ) -> bytes:
        """Create an input that fills an order.

        FillOrder inputs should not be signed (use ``encode_witness_no_signature``).
        """
        id_ptr, id_len = self._write_string(order_id)
        amt_ptr = self._new_wasm_amount(fill_amount)
        dest_ptr, dest_len = self._write_string(destination)
        return self._call_return_bytes(
            "encode_input_for_fill_order",
            id_ptr,
            id_len,
            amt_ptr,
            dest_ptr,
            dest_len,
            nonce,
            current_block_height,
            int(network),
        )

    @synchronized
    def encode_input_for_freeze_order(
        self, order_id: str, current_block_height: int, network: Network
    ) -> bytes:
        """Create an input that freezes an order.

        Order freezing is available only after the orders V1 fork.
        """
        id_ptr, id_len = self._write_string(order_id)
        return self._call_return_bytes(
            "encode_input_for_freeze_order", id_ptr, id_len, current_block_height, int(network)
        )
