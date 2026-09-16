"""Wallet lifecycle management (mirrors go-sdk/wallet/management.go)."""

from __future__ import annotations

from ._core import _WalletCore
from .types import (
    AccountInfo,
    AddressWithUsage,
    Balance,
    BestBlock,
    CreateWalletParams,
    CreateWalletResult,
    RecoverWalletParams,
    WalletInfo,
)


class ManagementMixin(_WalletCore):
    def create_wallet(self, params: CreateWalletParams) -> CreateWalletResult:
        """Create a new wallet file (optionally returning a generated mnemonic)."""
        data = self._call("wallet_create", params.to_json())
        return CreateWalletResult.from_json(data or {})

    def recover_wallet(self, params: RecoverWalletParams) -> None:
        """Recover a wallet from an existing mnemonic."""
        self._call_ignore("wallet_recover", params.to_json())

    def open_wallet(self, path: str, password: str = "") -> None:
        """Open a wallet file; an empty password is sent as JSON null."""
        self._call_ignore(
            "wallet_open",
            {
                "path": path,
                "password": password if password else None,
                "force_migrate_wallet_type": None,
                "hardware_wallet": None,
            },
        )

    def close_wallet(self) -> None:
        """Close the currently open wallet."""
        self._call_ignore("wallet_close", {})

    def get_wallet_info(self) -> WalletInfo:
        """Return info about the open wallet."""
        return self._call_model("wallet_info", {}, WalletInfo)

    def sync_wallet(self) -> None:
        """Trigger a wallet sync."""
        self._call_ignore("wallet_sync", {})

    def rescan_wallet(self) -> None:
        """Trigger a full chain rescan for the wallet."""
        self._call_ignore("wallet_rescan", {})

    def best_block(self) -> BestBlock:
        """Return the best block the wallet is aware of."""
        return self._call_model("wallet_best_block", {}, BestBlock)

    def create_account(self, name: str) -> AccountInfo:
        """Create a new account."""
        return self._call_model("account_create", {"name": name}, AccountInfo)

    def rename_account(self, account: int, name: str = "") -> None:
        """Rename an account; an empty name is sent as null (removes the name)."""
        self._call_ignore("account_rename", {"account": account, "name": name if name else None})

    def get_balance(self, account: int) -> Balance:
        """Return the confirmed balance of an account."""
        data = self._call(
            "account_balance",
            {"account": account, "utxo_states": ["Confirmed"], "with_locked": None},
        )
        return Balance.from_json(data or {})

    def new_address(self, account: int) -> str:
        """Derive a new receiving address for the account."""
        data = self._call("address_new", {"account": account})
        return str(data["address"])

    def show_receive_addresses(self, account: int) -> list[AddressWithUsage]:
        """Return the account's receive addresses with usage info."""
        data = self._call(
            "address_show",
            {"account": account, "include_change_addresses": False},
        )
        return [AddressWithUsage.from_json(a) for a in data or []]

    def reveal_public_key(self, account: int, address: str) -> str:
        """Reveal the hex public key backing an address."""
        data = self._call("address_reveal_public_key", {"account": account, "address": address})
        return str(data["public_key_hex"])

    def encrypt_private_keys(self, password: str) -> None:
        """Encrypt the wallet's private keys with a password."""
        self._call_ignore("wallet_encrypt_private_keys", {"password": password})

    def unlock_private_keys(self, password: str) -> None:
        """Unlock the wallet's private keys."""
        self._call_ignore("wallet_unlock_private_keys", {"password": password})

    def lock_private_keys(self) -> None:
        """Re-lock the wallet's private keys."""
        self._call_ignore("wallet_lock_private_keys", {})
