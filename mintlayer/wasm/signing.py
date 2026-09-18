"""Witness and signature encoding (mirrors go-sdk/wasm/signing.go)."""

from __future__ import annotations

from ._core import _WasmCore
from ._util import synchronized
from .types import Network, SignatureHashType, TxAdditionalInfo


class SigningMixin(_WasmCore):
    @synchronized
    def encode_witness(
        self,
        sighash_type: SignatureHashType,
        private_key: bytes,
        input_owner_dest: str,
        transaction: bytes,
        input_utxos: bytes,
        input_index: int,
        additional_info: TxAdditionalInfo,
        block_height: int,
        network: Network,
    ) -> bytes:
        """Sign a transaction input and return the encoded InputWitness.

        ``private_key`` is the raw encoded private key.
        ``input_owner_dest`` is the bech32m address that owns the input being signed.
        ``input_utxos`` is a concatenated set of optional UTXO outputs (one per
        input; prefix 0 for non-UTXO, 1+encoded-output for UTXO).
        """
        pk_ptr, pk_len = self._write_bytes(private_key)
        dest_ptr, dest_len = self._write_string(input_owner_dest)
        tx_ptr, tx_len = self._write_bytes(transaction)
        utxos_ptr, utxos_len = self._write_bytes(input_utxos)
        return self._call_return_bytes(
            "encode_witness",
            int(sighash_type),
            pk_ptr,
            pk_len,
            dest_ptr,
            dest_len,
            tx_ptr,
            tx_len,
            utxos_ptr,
            utxos_len,
            input_index,
            additional_info,
            block_height,
            int(network),
        )

    @synchronized
    def encode_witness_no_signature(self) -> bytes:
        """Return an InputWitness that carries no signature (for FillOrder inputs)."""
        return self._call_return_bytes_no_err("encode_witness_no_signature")

    @synchronized
    def encode_witness_htlc_spend(
        self,
        sighash_type: SignatureHashType,
        private_key: bytes,
        input_owner_dest: str,
        transaction: bytes,
        input_utxos: bytes,
        input_index: int,
        secret: bytes,
        additional_info: TxAdditionalInfo,
        block_height: int,
        network: Network,
    ) -> bytes:
        """Sign an HTLC input for spending (revealing the secret)."""
        pk_ptr, pk_len = self._write_bytes(private_key)
        dest_ptr, dest_len = self._write_string(input_owner_dest)
        tx_ptr, tx_len = self._write_bytes(transaction)
        utxos_ptr, utxos_len = self._write_bytes(input_utxos)
        sec_ptr, sec_len = self._write_bytes(secret)
        return self._call_return_bytes(
            "encode_witness_htlc_spend",
            int(sighash_type),
            pk_ptr,
            pk_len,
            dest_ptr,
            dest_len,
            tx_ptr,
            tx_len,
            utxos_ptr,
            utxos_len,
            input_index,
            sec_ptr,
            sec_len,
            additional_info,
            block_height,
            int(network),
        )

    @synchronized
    def encode_witness_htlc_refund_single_sig(
        self,
        sighash_type: SignatureHashType,
        private_key: bytes,
        input_owner_dest: str,
        transaction: bytes,
        input_utxos: bytes,
        input_index: int,
        additional_info: TxAdditionalInfo,
        block_height: int,
        network: Network,
    ) -> bytes:
        """Sign an HTLC input for refunding via a single-sig address."""
        pk_ptr, pk_len = self._write_bytes(private_key)
        dest_ptr, dest_len = self._write_string(input_owner_dest)
        tx_ptr, tx_len = self._write_bytes(transaction)
        utxos_ptr, utxos_len = self._write_bytes(input_utxos)
        return self._call_return_bytes(
            "encode_witness_htlc_refund_single_sig",
            int(sighash_type),
            pk_ptr,
            pk_len,
            dest_ptr,
            dest_len,
            tx_ptr,
            tx_len,
            utxos_ptr,
            utxos_len,
            input_index,
            additional_info,
            block_height,
            int(network),
        )

    @synchronized
    def encode_witness_htlc_refund_multisig(
        self,
        sighash_type: SignatureHashType,
        private_key: bytes,
        key_index: int,
        input_witness: bytes,
        multisig_challenge: bytes,
        transaction: bytes,
        input_utxos: bytes,
        input_index: int,
        additional_info: TxAdditionalInfo,
        block_height: int,
        network: Network,
    ) -> bytes:
        """Add a partial signature to an HTLC refund witness for a multisig refund address.

        ``key_index`` is the index of ``private_key`` within the multisig
        challenge. ``input_witness`` may be empty (first signer) or a previous
        partial result.
        """
        pk_ptr, pk_len = self._write_bytes(private_key)
        wit_ptr, wit_len = self._write_bytes(input_witness)
        chal_ptr, chal_len = self._write_bytes(multisig_challenge)
        tx_ptr, tx_len = self._write_bytes(transaction)
        utxos_ptr, utxos_len = self._write_bytes(input_utxos)
        return self._call_return_bytes(
            "encode_witness_htlc_refund_multisig",
            int(sighash_type),
            pk_ptr,
            pk_len,
            key_index,
            wit_ptr,
            wit_len,
            chal_ptr,
            chal_len,
            tx_ptr,
            tx_len,
            utxos_ptr,
            utxos_len,
            input_index,
            additional_info,
            block_height,
            int(network),
        )

    @synchronized
    def sign_challenge(self, private_key: bytes, message: bytes) -> bytes:
        """Sign an arbitrary message with the given private key.

        Use ``verify_challenge`` to verify the result.
        """
        pk_ptr, pk_len = self._write_bytes(private_key)
        msg_ptr, msg_len = self._write_bytes(message)
        return self._call_return_bytes("sign_challenge", pk_ptr, pk_len, msg_ptr, msg_len)

    @synchronized
    def verify_challenge(
        self, address: str, network: Network, signed_challenge: bytes, message: bytes
    ) -> bool:
        """Verify a challenge signature produced by ``sign_challenge``.

        ``address`` must be a pubkeyhash bech32m address.
        """
        addr_ptr, addr_len = self._write_string(address)
        sig_ptr, sig_len = self._write_bytes(signed_challenge)
        msg_ptr, msg_len = self._write_bytes(message)
        return self._call_return_bool(
            "verify_challenge",
            addr_ptr,
            addr_len,
            int(network),
            sig_ptr,
            sig_len,
            msg_ptr,
            msg_len,
        )

    @synchronized
    def sign_message_for_spending(self, private_key: bytes, message: bytes) -> bytes:
        """Sign a message for use as a transaction input witness.

        Use ``verify_signature_for_spending`` to verify the result.
        """
        pk_ptr, pk_len = self._write_bytes(private_key)
        msg_ptr, msg_len = self._write_bytes(message)
        return self._call_return_bytes(
            "sign_message_for_spending", pk_ptr, pk_len, msg_ptr, msg_len
        )

    @synchronized
    def verify_signature_for_spending(
        self, public_key: bytes, signature: bytes, message: bytes
    ) -> bool:
        """Verify a spending signature produced by ``sign_message_for_spending``."""
        pk_ptr, pk_len = self._write_bytes(public_key)
        sig_ptr, sig_len = self._write_bytes(signature)
        msg_ptr, msg_len = self._write_bytes(message)
        return self._call_return_bool(
            "verify_signature_for_spending", pk_ptr, pk_len, sig_ptr, sig_len, msg_ptr, msg_len
        )
