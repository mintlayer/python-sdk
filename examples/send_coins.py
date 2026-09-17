#!/usr/bin/env python3
# Copyright (c) 2026 Mintlayer Institutional FZCO
# Contact: hello@mintlayer.org
#
# Use of this source code is governed by an MIT license
# that can be found in the LICENSE file.

"""send-coins: the full manual transaction flow using the Mintlayer Python SDK.

1. Derive an account key and receiving address from a BIP-39 mnemonic.
2. Fetch spendable UTXOs for that address from the indexer.
3. Build an unsigned transaction (encode inputs and outputs).
4. Sign each input with encode_witness.
5. Submit the signed transaction to the indexer.

Usage:

    uv run python examples/send_coins.py \
        --mnemonic "word1 word2 ... word12" \
        --to mtc1qrecipient... \
        --amount 100000000000 \
        --indexer http://127.0.0.1:3000

NOTE: Secrets passed via command-line arguments are visible in
shell history and `ps` output; use stdin/env vars in production.

NOTE: This example sends ALL spendable UTXOs to the recipient with no change
output. It is intentionally minimal. Production code should select UTXOs,
compute fees, add a change output, and handle errors more robustly.
"""

from __future__ import annotations

import argparse
import logging
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


def total_atoms(utxos: list) -> int:
    """Sum the coin atoms across all Transfer/Coin UTXOs."""
    total = 0
    for u in utxos:
        try:
            if u.output.get("type") == "Transfer":
                value = u.output.get("value") or {}
                if value.get("type") == "Coin":
                    total += int(value["amount"]["atoms"])
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
    return total


def encode_utxo_entry(wasm: WasmClient, utxo_json: dict, network: Network) -> bytes:
    """Re-encode a JSON UTXO output into the binary form encode_witness expects.

    Format: 0x01 + <encoded output bytes> when the output can be re-encoded,
    0x00 otherwise (signing still succeeds for many output types).
    """
    try:
        if utxo_json.get("type") == "Transfer":
            value = utxo_json["value"]
            if value.get("type") == "Coin":
                encoded = wasm.encode_output_transfer(
                    Amount(atoms=value["amount"]["atoms"]),
                    value["destination"],
                    network,
                )
                return b"\x01" + encoded
    except (KeyError, TypeError, ValueError):
        pass
    return b"\x00"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mnemonic", required=True, help="BIP-39 mnemonic (12 or 24 words)")
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
    account_key = wasm.make_default_account_privkey(args.mnemonic, network)
    spend_key = wasm.make_receiving_address(account_key, args.key_index)
    pub_key = wasm.public_key_from_private_key(spend_key)
    from_addr = wasm.pubkey_to_pubkeyhash_address(pub_key, network)
    log.info("spending from: %s", from_addr)

    # ── 3. Fetch spendable UTXOs ─────────────────────────────────────────────
    indexer = IndexerClient(args.indexer)
    utxos = indexer.get_spendable_utxos(from_addr)

    if not utxos:
        log.fatal("no spendable UTXOs for %s", from_addr)
        sys.exit(1)
    log.info("found %d spendable UTXO(s)", len(utxos))

    total = total_atoms(utxos)
    send_amt = int(args.amount.strip())
    if total < send_amt:
        log.fatal("insufficient balance: have %d atoms, need %d atoms", total, send_amt)
        sys.exit(1)

    # ── 4. Encode inputs and collect per-input UTXO bytes ────────────────────
    encoded_inputs = b""
    all_utxo_bytes = b""
    for u in utxos:
        tx_id_bytes = bytes.fromhex(u.outpoint.source_id)
        src_id = wasm.encode_outpoint_source_id(tx_id_bytes, SOURCE_TRANSACTION)
        inp = wasm.encode_input_for_utxo(src_id, u.outpoint.index)
        encoded_inputs += inp
        all_utxo_bytes += encode_utxo_entry(wasm, u.output, network)

    # ── 5. Encode the transfer output ────────────────────────────────────────
    output = wasm.encode_output_transfer(Amount(atoms=args.amount), args.to, network)

    # ── 6. Build the unsigned transaction ────────────────────────────────────
    tx = wasm.encode_transaction(encoded_inputs, output, 0)
    tx_id = wasm.get_transaction_id(tx, True)
    log.info("unsigned tx id: %s", tx_id)

    # ── 7. Sign each input and collect witnesses ─────────────────────────────
    witness_bytes = b""
    for i in range(len(utxos)):
        witness = wasm.encode_witness(
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
        witness_bytes += witness

    # ── 8. Assemble the signed transaction ───────────────────────────────────
    signed_tx = wasm.encode_signed_transaction(tx, witness_bytes)
    log.info("signed tx (%d bytes)", len(signed_tx))

    # ── 9. Submit ────────────────────────────────────────────────────────────
    submitted_tx_id = indexer.submit_transaction(signed_tx.hex())
    print(f"submitted: {submitted_tx_id}")

    # Informational: in production, call wasm.estimate_transaction_size and
    # multiply by the fee rate from node.get_fee_rate or indexer.get_fee_rate
    # to compute the exact fee before building outputs.


if __name__ == "__main__":
    main()
