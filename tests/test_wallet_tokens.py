"""Token method tests for the wallet client.

Mirrors the "Tokens" section of go-sdk/wallet/client_test.go, pinning the
nested metadata wire shapes, both TokenSupply encodings, and the deliberate
``account_index`` key of lock_token_supply.
"""

from __future__ import annotations

from mintlayer.wallet import (
    Amount,
    ChangeAuthorityParams,
    Client,
    FreezeParams,
    IssueNFTParams,
    IssueTokenParams,
    IssueTokenResult,
    LockSupplyParams,
    MintParams,
    NFTMetadata,
    TokenMetadata,
    TokenSendParams,
    TokenSupply,
    UnfreezeParams,
    UnmintParams,
)

_ZERO_OPTIONS = {"in_top_x_mb": None, "broadcast_to_mempool": None}


def _send_result(tx_id: str) -> dict:
    return {
        "tx_id": tx_id,
        "fees": {"coins": {"atoms": "10000", "decimal": "0.0001"}, "tokens": {}},
        "broadcasted": True,
    }


def test_issue_token_lockable_supply(rpc_server) -> None:
    srv = rpc_server(result={"token_id": "tok1abc", "tx_id": "issue01"})
    client = Client(srv.url)
    got = client.issue_token(
        IssueTokenParams(
            account=0,
            destination_address="tmltool1auth",
            metadata=TokenMetadata(
                token_ticker="MYTKN",
                number_of_decimals=8,
                metadata_uri="https://example.com/token",
                token_supply=TokenSupply(type="Lockable"),
                is_freezable=False,
            ),
        )
    )
    assert got == IssueTokenResult(token_id="tok1abc", tx_id="issue01")
    assert srv.capture.method == "token_issue_new"
    # Lockable supply serialises without a content key.
    assert srv.capture.params["metadata"]["token_supply"] == {"type": "Lockable"}
    client.close()


def test_issue_token_fixed_supply_wire_shape(rpc_server) -> None:
    srv = rpc_server(result={"token_id": "tok1abc", "tx_id": "issue01"})
    client = Client(srv.url)
    client.issue_token(
        IssueTokenParams(
            account=0,
            destination_address="tmltool1auth",
            metadata=TokenMetadata(
                token_ticker="MYTKN",
                number_of_decimals=8,
                metadata_uri="https://example.com/token",
                token_supply=TokenSupply(type="Fixed", content=Amount(atoms="1000000")),
                is_freezable=True,
            ),
        )
    )
    assert srv.capture.method == "token_issue_new"
    # Fixed supply carries its amount inside a content object.
    assert srv.capture.params == {
        "account": 0,
        "destination_address": "tmltool1auth",
        "metadata": {
            "token_ticker": "MYTKN",
            "number_of_decimals": 8,
            "metadata_uri": "https://example.com/token",
            "token_supply": {"type": "Fixed", "content": {"atoms": "1000000"}},
            "is_freezable": True,
        },
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_issue_nft_metadata_nulls(rpc_server) -> None:
    srv = rpc_server(result={"token_id": "nft1abc", "tx_id": "nftissue01"})
    client = Client(srv.url)
    got = client.issue_nft(
        IssueNFTParams(
            account=0,
            destination_address="tmltool1dest",
            metadata=NFTMetadata(
                media_hash="a3f1e2d9c4",
                name="Sunset #1",
                description="A photograph of a sunset",
                ticker="SUNST",
            ),
        )
    )
    assert got.token_id == "nft1abc"
    assert srv.capture.method == "token_nft_issue_new"
    # Optional NFT metadata keys are always present, null when unset.
    assert srv.capture.params["metadata"] == {
        "media_hash": "a3f1e2d9c4",
        "name": "Sunset #1",
        "description": "A photograph of a sunset",
        "ticker": "SUNST",
        "creator": None,
        "icon_uri": None,
        "media_uri": None,
        "additional_metadata_uri": None,
    }
    client.close()


def test_mint_tokens(rpc_server) -> None:
    srv = rpc_server(result=_send_result("mint01"))
    client = Client(srv.url)
    got = client.mint_tokens(
        MintParams(
            account=0,
            token_id="tok1abc",
            address="tmltool1dest",
            amount=Amount(decimal="1000000"),
        )
    )
    assert got.tx_id == "mint01"
    assert srv.capture.method == "token_mint"
    assert srv.capture.params == {
        "account": 0,
        "token_id": "tok1abc",
        "address": "tmltool1dest",
        "amount": {"decimal": "1000000"},
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_unmint_tokens(rpc_server) -> None:
    srv = rpc_server(result=_send_result("unmint01"))
    client = Client(srv.url)
    got = client.unmint_tokens(
        UnmintParams(account=0, token_id="tok1abc", amount=Amount(decimal="5000"))
    )
    assert got.tx_id == "unmint01"
    assert srv.capture.method == "token_unmint"
    assert srv.capture.params == {
        "account": 0,
        "token_id": "tok1abc",
        "amount": {"decimal": "5000"},
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_lock_token_supply_uses_account_index_key(rpc_server) -> None:
    srv = rpc_server(result=_send_result("lock01"))
    client = Client(srv.url)
    got = client.lock_token_supply(LockSupplyParams(account_index=0, token_id="tok1abc"))
    assert got.tx_id == "lock01"
    assert srv.capture.method == "token_lock_supply"
    # The daemon route expects "account_index", never "account".
    assert srv.capture.params == {
        "account_index": 0,
        "token_id": "tok1abc",
        "options": _ZERO_OPTIONS,
    }
    assert "account" not in srv.capture.params
    client.close()


def test_freeze_token(rpc_server) -> None:
    srv = rpc_server(result=_send_result("freeze01"))
    client = Client(srv.url)
    got = client.freeze_token(FreezeParams(account=0, token_id="tok1abc", is_unfreezable=True))
    assert got.tx_id == "freeze01"
    assert srv.capture.method == "token_freeze"
    assert srv.capture.params == {
        "account": 0,
        "token_id": "tok1abc",
        "is_unfreezable": True,
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_unfreeze_token(rpc_server) -> None:
    srv = rpc_server(result=_send_result("unfreeze01"))
    client = Client(srv.url)
    got = client.unfreeze_token(UnfreezeParams(account=0, token_id="tok1abc"))
    assert got.tx_id == "unfreeze01"
    assert srv.capture.method == "token_unfreeze"
    assert srv.capture.params == {
        "account": 0,
        "token_id": "tok1abc",
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_change_token_authority(rpc_server) -> None:
    srv = rpc_server(result=_send_result("chauth01"))
    client = Client(srv.url)
    got = client.change_token_authority(
        ChangeAuthorityParams(account=0, token_id="tok1abc", address="tmltool1newauth")
    )
    assert got.tx_id == "chauth01"
    assert srv.capture.method == "token_change_authority"
    assert srv.capture.params == {
        "account": 0,
        "token_id": "tok1abc",
        "address": "tmltool1newauth",
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_send_token_alias_shares_token_send_method(rpc_server) -> None:
    srv = rpc_server(result=_send_result("sendtok01"))
    client = Client(srv.url)
    got = client.send_token(
        TokenSendParams(
            account=0,
            token_id="tok1abc",
            address="tmltool1dest",
            amount=Amount(decimal="100"),
        )
    )
    assert got.tx_id == "sendtok01"
    # Both spellings hit the same daemon route.
    assert srv.capture.method == "token_send"
    assert srv.capture.params["token_id"] == "tok1abc"
    client.close()
