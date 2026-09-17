#!/usr/bin/env python3
# Copyright (c) 2026 Mintlayer Institutional FZCO
# Contact: hello@mintlayer.org
#
# Use of this source code is governed by an MIT license
# that can be found in the LICENSE file.

"""issue-token: issue a new fungible token and mint initial supply via the
Mintlayer wallet daemon.

The flow:

1. Open the wallet (or connect to an already-open one).
2. Sync the wallet with the chain.
3. Derive a new receiving address to be the token authority.
4. Issue the token — the wallet signs, pays fees, and broadcasts the tx.
5. Mint an initial supply to the same address.

Usage:

    uv run python examples/issue_token.py \
        --wallet /path/to/wallet.dat \
        --ticker MYTOKEN \
        --decimals 2 \
        --supply 1000000 \
        --uri "https://example.com/token-metadata.json" \
        --wallet-rpc http://127.0.0.1:3034

Requirements:
- wallet-rpc-daemon must be running (or pass --wallet to open one).
- The wallet account must hold enough ML to pay issuance fees.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from mintlayer.wallet import (
    Amount,
    IssueTokenParams,
    MintParams,
    TokenMetadata,
    TokenSupply,
)
from mintlayer.wallet import (
    Client as WalletClient,
)

log = logging.getLogger("issue-token")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wallet", default="", help="path to wallet file (skip if already open)")
    parser.add_argument("--password", default="", help="wallet password (empty for unencrypted)")
    parser.add_argument("--ticker", required=True, help="token ticker symbol, e.g. MYTOKEN")
    parser.add_argument("--decimals", type=int, default=2, help="number of decimal places (0-18)")
    parser.add_argument("--supply", default="1000000", help="initial mint supply in smallest unit")
    parser.add_argument("--uri", default="", help="URL pointing to token metadata JSON")
    parser.add_argument("--wallet-rpc", default="http://127.0.0.1:3034", help="wallet RPC endpoint")
    parser.add_argument("--indexer", default="http://127.0.0.1:3000", help="indexer base URL")
    parser.add_argument("--account", type=int, default=0, help="wallet account index")
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=300,
        help="max seconds to wait for issuance confirmation",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # ── 1. Connect to the wallet daemon ──────────────────────────────────────
    wallet = WalletClient(args.wallet_rpc)

    # Open the wallet if a path was provided. Skip if the daemon already has
    # a wallet open (e.g. from a previous session).
    if args.wallet:
        try:
            wallet.open_wallet(args.wallet, args.password)
        except Exception as exc:
            log.fatal("open wallet: %s", exc)
            sys.exit(1)
        log.info("wallet opened: %s", args.wallet)

    # ── 2. Sync the wallet ───────────────────────────────────────────────────
    try:
        wallet.sync_wallet()
    except Exception as exc:
        # Non-fatal: the daemon may already be syncing.
        log.info("sync wallet: %s (continuing)", exc)

    # ── 3. Derive a fresh address to act as the token authority ──────────────
    #
    # The authority address is the address whose private key can later mint,
    # burn, freeze, or transfer the authority of the token.
    try:
        authority_addr = wallet.new_address(args.account)
    except Exception as exc:
        log.fatal("new address: %s", exc)
        sys.exit(1)
    log.info("authority address: %s", authority_addr)

    # Show the current balance so the user can confirm there are enough funds.
    try:
        balance = wallet.get_balance(args.account)
        log.info("account balance: %s atoms (%s ML)", balance.coins.atoms, balance.coins.decimal)
    except Exception as exc:
        log.info("get balance: %s (continuing)", exc)

    # ── 4. Issue the token ───────────────────────────────────────────────────
    #
    # Token supply type "Lockable" means the supply is unlimited until you
    # explicitly call lock_token_supply. Use "Fixed" (with a cap) or
    # "Unlimited" to change the supply policy.
    try:
        issue_result = wallet.issue_token(
            IssueTokenParams(
                account=args.account,
                destination_address=authority_addr,
                metadata=TokenMetadata(
                    token_ticker=args.ticker,
                    number_of_decimals=args.decimals,
                    metadata_uri=args.uri,
                    token_supply=TokenSupply(type="Lockable"),
                    is_freezable=False,
                ),
            )
        )
    except Exception as exc:
        log.fatal("issue token: %s", exc)
        sys.exit(1)

    print("token issued")
    print(f"  token id: {issue_result.token_id}")
    print(f"  tx id:    {issue_result.tx_id}")

    # ── 5. Mint initial supply ───────────────────────────────────────────────
    #
    # MintTokens creates new tokens and sends them to the given address.
    # The wallet must control the authority key.
    #
    # Minting requires the issuance transaction to be confirmed first, so poll
    # the indexer until it is (bounded by --wait-timeout).
    from mintlayer.indexer import Client as IndexerClient
    from mintlayer.indexer import HTTPError

    indexer = IndexerClient(args.indexer)
    deadline = time.monotonic() + args.wait_timeout
    while True:
        try:
            info = indexer.get_transaction(issue_result.tx_id)
        except HTTPError:
            info = None  # not indexed yet — keep polling
        if info and info.confirmations:
            log.info("issuance confirmed (%s confirmations)", info.confirmations)
            break
        if time.monotonic() >= deadline:
            log.warning(
                "issuance tx %s not confirmed within %ds; skipping mint (re-run once it confirms)",
                issue_result.tx_id,
                args.wait_timeout,
            )
            return
        log.info("waiting for issuance tx %s to confirm...", issue_result.tx_id)
        time.sleep(5)

    try:
        mint_result = wallet.mint_tokens(
            MintParams(
                account=args.account,
                token_id=issue_result.token_id,
                address=authority_addr,
                amount=Amount(atoms=args.supply),
            )
        )
    except Exception as exc:
        log.fatal(
            "mint tokens: %s\n\n"
            "Tip: the issuance tx may not have confirmed yet.\n"
            "Wait for confirmation and re-run with the token id.",
            exc,
        )
        sys.exit(1)

    print("tokens minted")
    print(f"  tx id: {mint_result.tx_id}")
    print(f"  fees:  {mint_result.fees.coins.atoms} atoms")


if __name__ == "__main__":
    main()
