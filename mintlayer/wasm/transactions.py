"""Transaction encoding and decoding (mirrors go-sdk/wasm/transactions.go)."""

from __future__ import annotations

from ._core import _WasmCore
from ._util import bool_to_int, synchronized
from .types import Network, SourceId, TxAdditionalInfo


class TransactionsMixin(_WasmCore):
    @synchronized
    def encode_transaction(self, inputs: bytes, outputs: bytes, flags: int) -> bytes:
        """Encode an unsigned transaction from its inputs and outputs.

        ``inputs`` and ``outputs`` must be concatenated encoded bytes from the
        respective ``encode_*`` functions.
        """
        in_ptr, in_len = self._write_bytes(inputs)
        out_ptr, out_len = self._write_bytes(outputs)
        return self._call_return_bytes(
            "encode_transaction", in_ptr, in_len, out_ptr, out_len, flags
        )

    @synchronized
    def encode_outpoint_source_id(self, id_: bytes, source_id: SourceId) -> bytes:
        """Encode a source ID (transaction hash or block reward ID) into binary form."""
        ptr, length = self._write_bytes(id_)
        return self._call_return_bytes_no_err(
            "encode_outpoint_source_id", ptr, length, int(source_id)
        )

    @synchronized
    def get_transaction_id(self, transaction: bytes, strict_byte_size: bool) -> str:
        """Return the transaction ID (hex string) for the given encoded transaction.

        Set ``strict_byte_size`` to require the bytes to represent exactly one
        Transaction object.
        """
        ptr, length = self._write_bytes(transaction)
        return self._call_return_string(
            "get_transaction_id", ptr, length, bool_to_int(strict_byte_size)
        )

    @synchronized
    def estimate_transaction_size(
        self, inputs: bytes, input_utxos_dests: list[str], outputs: bytes, network: Network
    ) -> int:
        """Estimate the encoded size of a signed transaction in bytes.

        ``input_utxos_dests`` must contain one address string per input (the
        spending destination of each UTXO).
        """
        in_ptr, in_len = self._write_bytes(inputs)
        dests_ptr, dests_indices = self._write_string_array(input_utxos_dests)
        try:
            out_ptr, out_len = self._write_bytes(outputs)
        except BaseException:
            # The callee never ran, so the host still owns the slots.
            self._dealloc_indices(dests_indices)
            raise
        # From here the callee owns the index array and the table slots (it
        # deallocs both); no post-call cleanup is needed.
        return self._call_return_u32(
            "estimate_transaction_size",
            in_ptr,
            in_len,
            dests_ptr,
            len(dests_indices),
            out_ptr,
            out_len,
            int(network),
        )

    @synchronized
    def encode_signed_transaction(self, transaction: bytes, signatures: bytes) -> bytes:
        """Combine an unsigned transaction with its witness signatures."""
        tx_ptr, tx_len = self._write_bytes(transaction)
        sig_ptr, sig_len = self._write_bytes(signatures)
        return self._call_return_bytes(
            "encode_signed_transaction", tx_ptr, tx_len, sig_ptr, sig_len
        )

    @synchronized
    def encode_partially_signed_transaction(
        self,
        transaction: bytes,
        signatures: bytes,
        input_utxos: bytes,
        input_destinations: bytes,
        htlc_secrets: bytes,
        additional_info: TxAdditionalInfo,
        network: Network,
    ) -> bytes:
        """Create a PartiallySignedTransaction object.

        ``additional_info`` provides pool/order data required for signing.
        """
        tx_ptr, tx_len = self._write_bytes(transaction)
        sig_ptr, sig_len = self._write_bytes(signatures)
        utxos_ptr, utxos_len = self._write_bytes(input_utxos)
        dests_ptr, dests_len = self._write_bytes(input_destinations)
        htlc_ptr, htlc_len = self._write_bytes(htlc_secrets)
        return self._call_return_bytes(
            "encode_partially_signed_transaction",
            tx_ptr,
            tx_len,
            sig_ptr,
            sig_len,
            utxos_ptr,
            utxos_len,
            dests_ptr,
            dests_len,
            htlc_ptr,
            htlc_len,
            additional_info,
            int(network),
        )

    @synchronized
    def decode_partially_signed_transaction_to_js(
        self, transaction: bytes, network: Network
    ) -> bytes:
        """Decode a partially signed transaction into a JSON object (raw JSON bytes)."""
        ptr, length = self._write_bytes(transaction)
        return self._call_return_json(
            "decode_partially_signed_transaction_to_js", ptr, length, int(network)
        )

    @synchronized
    def decode_signed_transaction_to_js(self, transaction: bytes, network: Network) -> bytes:
        """Decode a signed transaction into a JSON object (raw JSON bytes)."""
        ptr, length = self._write_bytes(transaction)
        return self._call_return_json("decode_signed_transaction_to_js", ptr, length, int(network))

    @synchronized
    def extract_htlc_secret(
        self,
        signed_tx: bytes,
        strict_byte_size: bool,
        htlc_outpoint_source_id: bytes,
        htlc_output_index: int,
    ) -> bytes:
        """Extract the pre-image secret from a signed HTLC-spend transaction."""
        tx_ptr, tx_len = self._write_bytes(signed_tx)
        src_ptr, src_len = self._write_bytes(htlc_outpoint_source_id)
        return self._call_return_bytes(
            "extract_htlc_secret",
            tx_ptr,
            tx_len,
            bool_to_int(strict_byte_size),
            src_ptr,
            src_len,
            htlc_output_index,
        )

    @synchronized
    def internal_verify_witness(
        self,
        sighash_type: int,
        input_owner_dest: str | None,
        witness: bytes,
        transaction: bytes,
        input_utxos: bytes,
        input_index: int,
        additional_info: TxAdditionalInfo,
        block_height: int,
        network: Network,
    ) -> None:
        """Verify an input witness against the transaction.

        ``input_owner_dest`` may be ``None`` for inputs where the destination is
        not required.
        """
        dest_ptr, dest_len = self._write_optional_string(input_owner_dest)
        wit_ptr, wit_len = self._write_bytes(witness)
        tx_ptr, tx_len = self._write_bytes(transaction)
        utxos_ptr, utxos_len = self._write_bytes(input_utxos)
        self._call_void_fallible(
            "internal_verify_witness",
            int(sighash_type),
            dest_ptr,
            dest_len,
            wit_ptr,
            wit_len,
            tx_ptr,
            tx_len,
            utxos_ptr,
            utxos_len,
            input_index,
            additional_info,
            block_height,
            int(network),
        )
