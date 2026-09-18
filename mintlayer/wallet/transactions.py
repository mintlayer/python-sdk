"""Transaction methods (mirrors go-sdk/wallet/transactions.go)."""

from __future__ import annotations

from typing import Any

from ._core import _WalletCore
from .types import (
    ComposedTx,
    ComposeParams,
    SendParams,
    SendResult,
    SignedTx,
    SubmitResult,
    SweepParams,
    TokenSendParams,
    TxInspection,
    TxOptions,
    UTXOSpendParams,
    WalletTx,
)


class TransactionsMixin(_WalletCore):
    def address_send(self, params: SendParams) -> SendResult:
        """Send coins from the account to an address."""
        return self._call_model("address_send", params.to_json(), SendResult)

    def token_send(self, params: TokenSendParams) -> SendResult:
        """Send tokens from the account to an address."""
        return self._call_model("token_send", params.to_json(), SendResult)

    def sweep_spendable(self, params: SweepParams) -> SendResult:
        """Sweep all spendable UTXOs to a destination address."""
        return self._call_model("address_sweep_spendable", params.to_json(), SendResult)

    def spend_utxo(self, params: UTXOSpendParams) -> SendResult:
        """Spend a specific UTXO."""
        return self._call_model("utxo_spend", params.to_json(), SendResult)

    def compose_transaction(self, params: ComposeParams) -> ComposedTx:
        """Compose (but do not sign) a transaction from inputs and raw outputs."""
        return self._call_model("transaction_compose", params.to_json(), ComposedTx)

    def sign_raw_transaction(self, account: int, raw_tx: str) -> SignedTx:
        """Sign a composed raw transaction with the account's keys."""
        return self._call_model(
            "account_sign_raw_transaction",
            {"account": account, "raw_tx": raw_tx, "options": TxOptions().to_json()},
            SignedTx,
        )

    def inspect_transaction(self, tx_hex: str) -> TxInspection:
        """Inspect a raw transaction (input/signature counts, estimated fees)."""
        return self._call_model("transaction_inspect", {"transaction": tx_hex}, TxInspection)

    def submit_transaction(self, tx_hex: str, do_not_store: bool = False) -> SubmitResult:
        """Submit a signed transaction to the node (trust policy is hardcoded
        to ``"Trusted"`` by the daemon route)."""
        return self._call_model(
            "node_submit_transaction",
            {
                "tx": tx_hex,
                "do_not_store": do_not_store,
                "options": {"trust_policy": "Trusted"},
            },
            SubmitResult,
        )

    def list_transactions_by_address(
        self, account: int, address: str | None, limit: int
    ) -> list[WalletTx]:
        """List account transactions; ``address=None`` filters to all addresses."""
        data = self._call(
            "transaction_list_by_address",
            {"account": account, "address": address, "limit": limit},
        )
        return [WalletTx.from_json(t) for t in data or []]

    def list_pending_transactions(self, account: int) -> list[str]:
        """List the account's pending (unconfirmed) transaction IDs."""
        data = self._call("transaction_list_pending", {"account": account})
        return [str(t) for t in data or []]

    def get_transaction(self, account: int, tx_id: str) -> Any:
        """Return a wallet transaction as raw decoded JSON."""
        return self._call("transaction_get", {"account": account, "transaction_id": tx_id})

    def abandon_transaction(self, account: int, tx_id: str) -> None:
        """Abandon a pending transaction."""
        self._call_ignore("transaction_abandon", {"account": account, "transaction_id": tx_id})

    def deposit_data(self, account: int, data_hex: str) -> SendResult:
        """Create a DataDeposit output carrying arbitrary hex data."""
        return self._call_model(
            "address_deposit_data",
            {"account": account, "data": data_hex, "options": TxOptions().to_json()},
            SendResult,
        )
