"""Transaction intents (mirrors go-sdk/wasm/intent.go)."""

from __future__ import annotations

from ._core import _WasmCore
from ._util import synchronized
from .types import Network


class IntentMixin(_WasmCore):
    @synchronized
    def make_transaction_intent_message_to_sign(self, intent: str, transaction_id: str) -> bytes:
        """Return the canonical message that must be signed for a transaction intent.

        ``transaction_id`` should be a hex-encoded transaction ID returned by
        ``get_transaction_id``.
        """
        int_ptr, int_len = self._write_string(intent)
        txid_ptr, txid_len = self._write_string(transaction_id)
        return self._call_return_bytes(
            "make_transaction_intent_message_to_sign", int_ptr, int_len, txid_ptr, txid_len
        )

    @synchronized
    def encode_signed_transaction_intent(
        self, signed_message: bytes, signatures: list[bytes]
    ) -> bytes:
        """Combine a signed message with per-input signatures into a SignedTransactionIntent.

        ``signed_message`` must be produced by
        ``make_transaction_intent_message_to_sign``. ``signatures`` is one raw
        signature per transaction input, each produced by ``sign_challenge``.
        """
        msg_ptr, msg_len = self._write_bytes(signed_message)
        sigs_ptr, sigs_indices, sigs_buffers = self._write_uint8_array_array(signatures)
        try:
            return self._call_return_bytes(
                "encode_signed_transaction_intent", msg_ptr, msg_len, sigs_ptr, len(sigs_indices)
            )
        finally:
            self._dealloc_indices(sigs_indices)
            for ptr, length in sigs_buffers:
                self._free_wasm(ptr, length)

    @synchronized
    def verify_transaction_intent(
        self,
        expected_signed_message: bytes,
        encoded_signed_intent: bytes,
        input_destinations: list[str],
        network: Network,
    ) -> None:
        """Verify a signed transaction intent.

        ``input_destinations`` contains one bech32m address per transaction input.
        """
        msg_ptr, msg_len = self._write_bytes(expected_signed_message)
        intent_ptr, intent_len = self._write_bytes(encoded_signed_intent)
        dests_ptr, dests_indices = self._write_string_array(input_destinations)
        try:
            self._call_void_fallible(
                "verify_transaction_intent",
                msg_ptr,
                msg_len,
                intent_ptr,
                intent_len,
                dests_ptr,
                len(dests_indices),
                int(network),
            )
        finally:
            self._dealloc_indices(dests_indices)
