"""Wallet lifecycle management tests.

Mirrors the "Wallet management" section of go-sdk/wallet/client_test.go,
pinning the exact RPC method names and params shapes on the wire.
"""

from __future__ import annotations

import pytest

from mintlayer.wallet import (
    AccountInfo,
    AddressWithUsage,
    Amount,
    Balance,
    BestBlock,
    Client,
    CreateWalletParams,
    CreateWalletResult,
    JSONRPCError,
    MnemonicResult,
    RecoverWalletParams,
    WalletInfo,
)
from mintlayer.wallet.types import RevealPublicKeyResult

_MNEMONIC = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12"


def test_create_wallet_newly_generated(rpc_server) -> None:
    result = {"mnemonic": {"type": "NewlyGenerated", "content": {"mnemonic": _MNEMONIC}}}
    srv = rpc_server(result=result)
    client = Client(srv.url)
    got = client.create_wallet(CreateWalletParams(path="/tmp/test.db", store_seed_phrase=True))
    assert srv.capture.method == "wallet_create"
    assert got.mnemonic is not None
    assert got.mnemonic.type == "NewlyGenerated"
    assert got.mnemonic.content is not None
    assert got.mnemonic.content.mnemonic == _MNEMONIC
    client.close()


def test_create_wallet_user_provided_content_null(rpc_server) -> None:
    srv = rpc_server(result={"mnemonic": {"type": "UserProvided", "content": None}})
    client = Client(srv.url)
    got = client.create_wallet(CreateWalletParams(path="/tmp/test.db", store_seed_phrase=False))
    assert got.mnemonic is not None
    assert got.mnemonic.type == "UserProvided"
    assert got.mnemonic.content is None
    client.close()


def test_create_wallet_without_mnemonic(rpc_server) -> None:
    srv = rpc_server(result={})
    client = Client(srv.url)
    got = client.create_wallet(CreateWalletParams(path="/tmp/test.db", store_seed_phrase=True))
    assert got == CreateWalletResult(mnemonic=None)
    client.close()


# ── MnemonicResult.from_json content validation (direct decode tests) ────────


def test_mnemonic_result_from_json_valid_content() -> None:
    got = MnemonicResult.from_json({"type": "NewlyGenerated", "content": {"mnemonic": _MNEMONIC}})
    assert got.type == "NewlyGenerated"
    assert got.content is not None
    assert got.content.mnemonic == _MNEMONIC


def test_mnemonic_result_from_json_null_content() -> None:
    got = MnemonicResult.from_json({"type": "UserProvided", "content": None})
    assert got.type == "UserProvided"
    assert got.content is None


def test_mnemonic_result_from_json_non_dict_content_raises() -> None:
    """A non-dict content raises ValueError, never a str()-coerced field."""
    with pytest.raises(ValueError, match="invalid content"):
        MnemonicResult.from_json({"type": "NewlyGenerated", "content": "oops"})  # type: ignore[dict-item]


def test_mnemonic_result_from_json_missing_mnemonic_key_raises() -> None:
    """A payload without the required ``mnemonic`` key raises ValueError
    ("malformed payload") instead of a bare kwargs TypeError."""
    with pytest.raises(ValueError, match="malformed payload"):
        MnemonicResult.from_json({"type": "NewlyGenerated", "content": {"seed": "x"}})


def test_create_wallet_wire_shape(rpc_server) -> None:
    srv = rpc_server(result={})
    client = Client(srv.url)
    client.create_wallet(CreateWalletParams(path="/tmp/test.db", store_seed_phrase=True))
    assert srv.capture.params == {
        "path": "/tmp/test.db",
        "store_seed_phrase": True,
        "mnemonic": None,
        "passphrase": None,
        "hardware_wallet": None,
    }
    client.close()


def test_recover_wallet(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.recover_wallet(
        RecoverWalletParams(
            path="/tmp/recovered.db",
            store_seed_phrase=False,
            mnemonic=_MNEMONIC,
        )
    )
    assert srv.capture.method == "wallet_recover"
    assert srv.capture.params == {
        "path": "/tmp/recovered.db",
        "store_seed_phrase": False,
        "mnemonic": _MNEMONIC,
        "passphrase": None,
        "hardware_wallet": None,
    }
    client.close()


@pytest.mark.parametrize(
    ("password", "wire_password"),
    [("", None), ("hunter2", "hunter2")],
    ids=["empty_password_null", "password_sent_verbatim"],
)
def test_open_wallet(rpc_server, password: str, wire_password: str | None) -> None:
    """An empty password is sent as JSON null; a real one verbatim."""
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.open_wallet("/tmp/test.db", password)
    assert srv.capture.method == "wallet_open"
    assert srv.capture.params == {
        "path": "/tmp/test.db",
        "password": wire_password,
        "force_migrate_wallet_type": None,
        "hardware_wallet": None,
    }
    client.close()


def test_close_wallet(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.close_wallet()
    assert srv.capture.method == "wallet_close"
    assert srv.capture.params == {}
    client.close()


def test_get_wallet_info(rpc_server) -> None:
    srv = rpc_server(
        result={
            "wallet_id": "aabb1234",
            "account_names": ["Main", "Savings"],
            "extra_info": {"type": "SoftwareWallet"},
        }
    )
    client = Client(srv.url)
    got = client.get_wallet_info()
    assert isinstance(got, WalletInfo)
    assert got.wallet_id == "aabb1234"
    assert got.account_names == ["Main", "Savings"]
    assert got.extra_info.type == "SoftwareWallet"
    assert srv.capture.method == "wallet_info"
    assert srv.capture.params == {}
    client.close()


def test_get_wallet_info_null_result_raises(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    with pytest.raises(JSONRPCError, match="expected object result"):
        client.get_wallet_info()
    client.close()


def test_sync_wallet(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.sync_wallet()
    assert srv.capture.method == "wallet_sync"
    assert srv.capture.params == {}
    client.close()


def test_rescan_wallet(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.rescan_wallet()
    assert srv.capture.method == "wallet_rescan"
    assert srv.capture.params == {}
    client.close()


def test_best_block(rpc_server) -> None:
    srv = rpc_server(result={"height": 42000, "id": "deadbeef"})
    client = Client(srv.url)
    got = client.best_block()
    assert got == BestBlock(height=42000, id="deadbeef")
    assert srv.capture.method == "wallet_best_block"
    assert srv.capture.params == {}
    client.close()


def test_create_account(rpc_server) -> None:
    srv = rpc_server(result={"account": 1, "name": "Savings"})
    client = Client(srv.url)
    got = client.create_account("Savings")
    assert got == AccountInfo(account=1, name="Savings")
    assert srv.capture.method == "account_create"
    assert srv.capture.params == {"name": "Savings"}
    client.close()


def test_rename_account(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.rename_account(0, "Main")
    assert srv.capture.method == "account_rename"
    assert srv.capture.params == {"account": 0, "name": "Main"}
    client.close()


def test_rename_account_empty_name_sent_as_null(rpc_server) -> None:
    """An empty name is sent as null (clears the account name)."""
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.rename_account(0)
    assert srv.capture.method == "account_rename"
    assert srv.capture.params == {"account": 0, "name": None}
    client.close()


def test_get_balance(rpc_server) -> None:
    result = {
        "coins": {"atoms": "1000000000000", "decimal": "10000.0"},
        "tokens": {"tok1abc": {"atoms": "500000000"}},
    }
    srv = rpc_server(result=result)
    client = Client(srv.url)
    got = client.get_balance(0)
    assert isinstance(got, Balance)
    assert got.coins == Amount(atoms="1000000000000", decimal="10000.0")
    assert got.tokens == {"tok1abc": Amount(atoms="500000000")}
    assert srv.capture.method == "account_balance"
    # Pinned option keys: confirmed-only UTXO states, locked UTXOs not merged.
    assert srv.capture.params == {
        "account": 0,
        "utxo_states": ["Confirmed"],
        "with_locked": None,
    }
    client.close()


def test_new_address(rpc_server) -> None:
    srv = rpc_server(result={"address": "tmltool1abc"})
    client = Client(srv.url)
    assert client.new_address(0) == "tmltool1abc"
    assert srv.capture.method == "address_new"
    assert srv.capture.params == {"account": 0}
    client.close()


def test_new_address_null_result_raises(rpc_server) -> None:
    """A JSON null result raises JSONRPCError, not an opaque TypeError."""
    srv = rpc_server(result=None)
    client = Client(srv.url)
    with pytest.raises(JSONRPCError, match="expected object result, got null"):
        client.new_address(0)
    client.close()


def test_show_receive_addresses(rpc_server) -> None:
    result = [
        {"address": "tmltool1abc", "used": False, "coins": {"atoms": "0"}},
        {"address": "tmltool1def", "used": True, "coins": {"atoms": "5000000000"}},
    ]
    srv = rpc_server(result=result)
    client = Client(srv.url)
    got = client.show_receive_addresses(0)
    assert got == [
        AddressWithUsage(address="tmltool1abc", used=False, coins=Amount(atoms="0")),
        AddressWithUsage(address="tmltool1def", used=True, coins=Amount(atoms="5000000000")),
    ]
    assert srv.capture.method == "address_show"
    # Change addresses are never included.
    assert srv.capture.params == {"account": 0, "include_change_addresses": False}
    client.close()


def test_show_receive_addresses_null_result_returns_empty(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.show_receive_addresses(0) == []
    client.close()


def test_reveal_public_key(rpc_server) -> None:
    result = {"public_key_hex": "02aabbccdd", "public_key_address": "tmltool1pubkey"}
    srv = rpc_server(result=result)
    client = Client(srv.url)
    assert client.reveal_public_key(0, "tmltool1abc") == "02aabbccdd"
    assert srv.capture.method == "address_reveal_public_key"
    assert srv.capture.params == {"account": 0, "address": "tmltool1abc"}
    client.close()


def test_reveal_public_key_result_decode() -> None:
    got = RevealPublicKeyResult.from_json(
        {"public_key_hex": "02aabbccdd", "public_key_address": "tmltool1pubkey"}
    )
    assert got.public_key_hex == "02aabbccdd"
    assert got.public_key_address == "tmltool1pubkey"


def test_reveal_public_key_null_result_raises(rpc_server) -> None:
    """A JSON null result raises JSONRPCError, not an opaque TypeError."""
    srv = rpc_server(result=None)
    client = Client(srv.url)
    with pytest.raises(JSONRPCError, match="expected object result, got null"):
        client.reveal_public_key(0, "tmltool1abc")
    client.close()


def test_encrypt_private_keys(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.encrypt_private_keys("s3cr3t")
    assert srv.capture.method == "wallet_encrypt_private_keys"
    assert srv.capture.params == {"password": "s3cr3t"}
    client.close()


def test_unlock_private_keys(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.unlock_private_keys("s3cr3t")
    assert srv.capture.method == "wallet_unlock_private_keys"
    assert srv.capture.params == {"password": "s3cr3t"}
    client.close()


def test_lock_private_keys(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.lock_private_keys()
    assert srv.capture.method == "wallet_lock_private_keys"
    assert srv.capture.params == {}
    client.close()
