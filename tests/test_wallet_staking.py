"""Staking and delegation tests for the wallet client.

Mirrors the "Staking" section of go-sdk/wallet/client_test.go, pinning the
pool params wire shape, the account-less pool-balance route, and the bare
string -> enum mapping of the staking status.
"""

from __future__ import annotations

from mintlayer.wallet import (
    Amount,
    Client,
    CreateDelegationParams,
    CreateDelegationResult,
    CreatePoolParams,
    DecommissionParams,
    DelegateParams,
    DelegationInfo,
    OwnedPool,
    StakingStatus,
    WithdrawParams,
)

_ZERO_OPTIONS = {"in_top_x_mb": None, "broadcast_to_mempool": None}


def _send_result(tx_id: str) -> dict:
    return {
        "tx_id": tx_id,
        "fees": {"coins": {"atoms": "10000", "decimal": "0.0001"}, "tokens": {}},
        "broadcasted": True,
    }


def test_create_stake_pool(rpc_server) -> None:
    srv = rpc_server(result=_send_result("pool01"))
    client = Client(srv.url)
    got = client.create_stake_pool(
        CreatePoolParams(
            account=0,
            amount=Amount(decimal="40000"),
            cost_per_block=Amount(decimal="1"),
            margin_ratio_per_thousand="5%",
            decommission_address="tmltool1decom",
        )
    )
    assert got.tx_id == "pool01"
    assert got.broadcasted is True
    assert srv.capture.method == "staking_create_pool"
    # The margin ratio string passes through untouched; optional addresses
    # stay explicit nulls.
    assert srv.capture.params == {
        "account": 0,
        "amount": {"decimal": "40000"},
        "cost_per_block": {"decimal": "1"},
        "margin_ratio_per_thousand": "5%",
        "decommission_address": "tmltool1decom",
        "staker_address": None,
        "vrf_public_key": None,
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_decommission_stake_pool(rpc_server) -> None:
    srv = rpc_server(result=_send_result("decom01"))
    client = Client(srv.url)
    got = client.decommission_stake_pool(
        DecommissionParams(account=0, pool_id="pool1abc", output_address="tmltool1dest")
    )
    assert got.tx_id == "decom01"
    assert srv.capture.method == "staking_decommission_pool"
    assert srv.capture.params == {
        "account": 0,
        "pool_id": "pool1abc",
        "output_address": "tmltool1dest",
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_list_owned_pools(rpc_server) -> None:
    result = [
        {
            "pool_id": "pool1abc",
            "pledge": {"atoms": "40000000000000"},
            "balance": {"atoms": "50000000000000"},
            "margin_ratio_per_thousand": "5%",
            "cost_per_block": {"atoms": "100000000"},
        }
    ]
    srv = rpc_server(result=result)
    client = Client(srv.url)
    got = client.list_owned_pools(0)
    assert got == [
        OwnedPool(
            pool_id="pool1abc",
            pledge=Amount(atoms="40000000000000"),
            balance=Amount(atoms="50000000000000"),
            margin_ratio_per_thousand="5%",
            cost_per_block=Amount(atoms="100000000"),
        )
    ]
    assert srv.capture.method == "staking_list_pools"
    assert srv.capture.params == {"account": 0}
    client.close()


def test_list_owned_pools_null_result_returns_empty(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.list_owned_pools(0) == []
    client.close()


def test_get_pool_balance_account_not_sent(rpc_server) -> None:
    srv = rpc_server(result={"balance": {"atoms": "50000000000000", "decimal": "500000.0"}})
    client = Client(srv.url)
    got = client.get_pool_balance(0, "pool1abc")
    assert got == Amount(atoms="50000000000000", decimal="500000.0")
    assert srv.capture.method == "staking_pool_balance"
    # The daemon route takes only the pool id: the account argument is
    # accepted for API consistency but never serialised.
    assert srv.capture.params == {"pool_id": "pool1abc"}
    client.close()


def test_start_staking(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.start_staking(0)
    assert srv.capture.method == "staking_start"
    assert srv.capture.params == {"account": 0}
    client.close()


def test_stop_staking(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.stop_staking(0)
    assert srv.capture.method == "staking_stop"
    assert srv.capture.params == {"account": 0}
    client.close()


def test_get_staking_status_active(rpc_server) -> None:
    srv = rpc_server(result="Staking")
    client = Client(srv.url)
    assert client.get_staking_status(0) is StakingStatus.ACTIVE
    assert srv.capture.method == "staking_status"
    assert srv.capture.params == {"account": 0}
    client.close()


def test_get_staking_status_inactive(rpc_server) -> None:
    srv = rpc_server(result="NotStaking")
    client = Client(srv.url)
    assert client.get_staking_status(0) is StakingStatus.INACTIVE
    client.close()


def test_create_delegation(rpc_server) -> None:
    srv = rpc_server(result={"delegation_id": "deleg1abc", "tx_id": "delegtx01"})
    client = Client(srv.url)
    got = client.create_delegation(
        CreateDelegationParams(account=0, address="tmltool1owner", pool_id="pool1abc")
    )
    assert got == CreateDelegationResult(delegation_id="deleg1abc", tx_id="delegtx01")
    assert srv.capture.method == "delegation_create"
    assert srv.capture.params == {
        "account": 0,
        "address": "tmltool1owner",
        "pool_id": "pool1abc",
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_delegate_staking(rpc_server) -> None:
    srv = rpc_server(result=_send_result("stake01"))
    client = Client(srv.url)
    got = client.delegate_staking(
        DelegateParams(account=0, amount=Amount(decimal="1000"), delegation_id="deleg1abc")
    )
    assert got.tx_id == "stake01"
    assert srv.capture.method == "delegation_stake"
    assert srv.capture.params == {
        "account": 0,
        "amount": {"decimal": "1000"},
        "delegation_id": "deleg1abc",
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_withdraw_from_delegation(rpc_server) -> None:
    srv = rpc_server(result=_send_result("withdraw01"))
    client = Client(srv.url)
    got = client.withdraw_from_delegation(
        WithdrawParams(
            account=0,
            address="tmltool1dest",
            amount=Amount(decimal="500"),
            delegation_id="deleg1abc",
        )
    )
    assert got.tx_id == "withdraw01"
    assert srv.capture.method == "delegation_withdraw"
    assert srv.capture.params == {
        "account": 0,
        "address": "tmltool1dest",
        "amount": {"decimal": "500"},
        "delegation_id": "deleg1abc",
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_list_delegations(rpc_server) -> None:
    result = [
        {
            "delegation_id": "deleg1abc",
            "pool_id": "pool1abc",
            "balance": {"atoms": "1000000000000"},
        }
    ]
    srv = rpc_server(result=result)
    client = Client(srv.url)
    got = client.list_delegations(0)
    assert got == [
        DelegationInfo(
            delegation_id="deleg1abc",
            pool_id="pool1abc",
            balance=Amount(atoms="1000000000000"),
        )
    ]
    assert srv.capture.method == "delegation_list_ids"
    assert srv.capture.params == {"account": 0}
    client.close()
