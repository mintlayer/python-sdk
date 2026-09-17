#!/usr/bin/env python3
# Copyright (c) 2026 Mintlayer Institutional FZCO
# Contact: hello@mintlayer.org
#
# Use of this source code is governed by an MIT license
# that can be found in the LICENSE file.

"""send-coins: the full manual transaction flow using the Mintlayer Python SDK.

1. Derive an account key and receiving address from a BIP-39 mnemonic.
2. Fetch spendable UTXOs for that address from the indexer.
3. Build an unsigned transaction (encode inputs, recipient output, change).
4. Sign each input with encode_witness.
5. Submit the signed transaction to the indexer.

Usage:

    uv run python examples/send_coins.py \\
        --to mtc1qrecipient... \\
        --amount 100000000000 \\
        --indexer http://127.0.0.1:3000

The mnemonic can be passed via ``--mnemonic``, the ``MNEMONIC`` environment
variable, or a hidden interactive prompt — avoiding shell history and ``ps``
exposure.

NOTE: This is a teaching example: fees are estimated from the indexer fee
rate, the remainder is returned to the source address as change, and only
plain Transfer/Coin UTXOs are selected. Production code should use the wallet
daemon or a proper coin-selection and fee-bumping strategy.
"""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import sys

from mintlayer.indexer import Client as IndexerClient
from mintlayer.wasm import (
    SOURCE_TRANSACTION,
    Amount,
    Network,
    SignatureHashType,
    TxAdditionalInfo,
)
from mintlayer.wasm import (
    Client as WasmClient,
)

log = logging.getLogger("send-coins")

FEE_RATE_PER_KB_FALLBACK = 100_000  # atoms/KB used when the indexer has no fee data


def is_coin_transfer(output: object) -> bool:
    """Whether a decoded UTXO output is a plain Transfer of native coins."""
    if not isinstance(output, dict) or output.get("type") != "Transfer":
        return False
    value = output.get("value")
    return isinstance(value, dict) and value.get("type") == "Coin"


def output_atoms(output: dict) -> int:
    """Atom count of a Transfer/Coin output (pre-validated by is_coin_transfer)."""
    return int(output["value"]["amount"]["atoms"])


def encode_utxo_entry(wasm: WasmClient, utxo_json: dict, network: Network) -> bytes:
    """Re-encode a JSON UTXO output into the binary form encode_witness expects.

    Format: ``0x01 + <encoded output bytes>``. Signatures only verify on-chain
    if the sighash covers the real output, so a re-encoding failure is fatal
    rather than silently downgraded to a non-UTXO (``0x00``) entry.
    """
    if utxo_json.get("type") == "Transfer":
        value = utxo_json["value"]
        if value.get("type") == "Coin":
            encoded = wasm.encode_output_transfer(
                Amount(atoms=value["amount"]["atoms"]),
                value["destination"],
                network,
            )
            return b"\x01" + encoded
    raise ValueError(f"unsupported UTXO output type for minimal send: {utxo_json.get('type')!r}")


def resolve_mnemonic(cli_value: str) -> str:
    """CLI argument, then the ``MNEMONIC`` env var, then a hidden prompt."""
    if cli_value:
        return cli_value
    env = os.environ.get("MNEMONIC", "")
    if env:
        log.info("using mnemonic from the MNEMONIC environment variable")
        return env
    return getpass.getpass("BIP-39 mnemonic (input hidden): ")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mnemonic",
        default="",
        help="BIP-39 mnemonic (insecure: visible in ps/shell history); prefer $MNEMONIC or prompt",
    )
    parser.add_argument("--to", required=True, help="recipient bech32m address")
    parser.add_argument("--amount", required=True, help="amount to send in atoms (1 ML = 1e11)")
    parser.add_argument("--indexer", default="http://127.0.0.1:3000", help="indexer base URL")
    parser.add_argument("--key-index", type=int, default=0, help="receiving address key index")
    parser.add_argument(
        "--network", type=int, default=0, help="0=mainnet 1=testnet 2=regtest 3=signet"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    network = Network(args.network)

    # ── 1. Initialise the WASM cryptography runtime ──────────────────────────
    wasm = WasmClient()

    # ── 2. Derive the spending key and address ───────────────────────────────
    mnemonic = resolve_mnemonic(args.mnemonic)
    account_key = wasm.make_default_account_privkey(mnemonic, network)
    spend_key = wasm.make_receiving_address(account_key, args.key_index)
    pub_key = wasm.public_key_from_private_key(spend_key)
    from_addr = wasm.pubkey_to_pubkeyhash_address(pub_key, network)
    log.info("spending from: %s", from_addr)

    # ── 3. Fetch spendable UTXOs (this minimal send only handles Coin) ───────
    indexer = IndexerClient(args.indexer)
    all_utxos = indexer.get_spendable_utxos(from_addr)

    utxos = [u for u in all_utxos if is_coin_transfer(u.output)]
    for u in all_utxos:
        if not is_coin_transfer(u.output):
            output_type = u.output.get("type") if isinstance(u.output, dict) else None
            log.warning("skipping non-Coin UTXO (type=%s)", output_type)

    if not utxos:
        log.fatal("no spendable Coin UTXOs for %s", from_addr)
        sys.exit(1)
    log.info("found %d spendable UTXO(s)", len(utxos))

    total = sum(output_atoms(u.output) for u in utxos)
    send_amt = int(args.amount.strip())
    if send_amt <= 0:
        log.fatal("amount must be positive")
        sys.exit(1)
    if total < send_amt:
        log.fatal("insufficient balance: have %d atoms, need %d atoms", total, send_amt)
        sys.exit(1)

    # ── 4. Encode inputs and collect per-input UTXO bytes ────────────────────
    encoded_inputs = b""
    all_utxo_bytes = b""
    for u in utxos:
        tx_id_bytes = bytes.fromhex(u.outpoint.source_id)
        src_id = wasm.encode_outpoint_source_id(tx_id_bytes, SOURCE_TRANSACTION)
        encoded_inputs += wasm.encode_input_for_utxo(src_id, u.outpoint.index)
        all_utxo_bytes += encode_utxo_entry(wasm, u.output, network)

    # ── 5. Fee rate, then build the transaction with change ──────────────────
    try:
        fee_rate = int(indexer.get_fee_rate())  # atoms per kilobyte
    except Exception as exc:
        log.warning(
            "fee rate lookup failed (%s); using fallback %d atoms/KB",
            exc,
            FEE_RATE_PER_KB_FALLBACK,
        )
        fee_rate = FEE_RATE_PER_KB_FALLBACK

    def build(fee: int) -> tuple[bytes, int]:
        """Recipient output + change output; return (tx, estimated size)."""
        change = total - send_amt - fee
        if change < 0:
            raise ValueError(f"insufficient balance for fee: have {total}, need {send_amt} + {fee}")
        outputs = wasm.encode_output_transfer(Amount(atoms=str(send_amt)), args.to, network)
        if change > 0:
            outputs += wasm.encode_output_transfer(Amount(atoms=str(change)), from_addr, network)
        tx = wasm.encode_transaction(encoded_inputs, outputs, 0)
        size = wasm.estimate_transaction_size(tx, [from_addr] * len(utxos), outputs, network)
        return tx, size

    # The fee depends on the tx size, which depends on the change amount's
    # digit count; the loop converges in a couple of passes.
    fee = fee_rate  # start from 1 KB worth of fees
    tx, size = build(fee)
    for _ in range(4):
        new_fee = max(1, -(-size // 1000) * fee_rate)  # ceil(size / 1000) * rate
        if new_fee == fee:
            break
        fee = new_fee
        tx, size = build(fee)

    if total - send_amt - fee <= 0:
        log.fatal("balance %d cannot cover amount %d plus fee %d", total, send_amt, fee)
        sys.exit(1)

    tx_id = wasm.get_transaction_id(tx, True)
    log.info("unsigned tx id: %s (fee: %d atoms)", tx_id, fee)

    # ── 6. Sign each input and collect witnesses ─────────────────────────────
    witness_bytes = b""
    for i in range(len(utxos)):
        witness_bytes += wasm.encode_witness(
            SignatureHashType.SIGHASH_ALL,
            spend_key,
            from_addr,
            tx,
            all_utxo_bytes,
            i,
            TxAdditionalInfo(),
            0,  # block height (0 = no lock-time constraint)
            network,
        )

    # ── 7. Assemble the signed transaction ───────────────────────────────────
    signed_tx = wasm.encode_signed_transaction(tx, witness_bytes)
    log.info("signed tx (%d bytes)", len(signed_tx))

    # ── 8. Submit ────────────────────────────────────────────────────────────
    submitted_tx_id = indexer.submit_transaction(signed_tx.hex())
    print(f"submitted: {submitted_tx_id}")


if __name__ == "__main__":
    main()
