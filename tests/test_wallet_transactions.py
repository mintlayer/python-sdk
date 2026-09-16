"""Transaction method tests for the wallet client.

Mirrors the "Transactions" section of go-sdk/wallet/client_test.go, pinning
the exact RPC method names, the always-present TxOptions keys, and the
omitempty behaviour of ``selected_utxos``.
"""

from __future__ import annotations

import pytest

from mintlayer.wallet import (
    Amount,
    Client,
    ComposeParams,
    FeesBreakdown,
    SendParams,
    SendResult,
    SignedTx,
    SubmitResult,
    SweepParams,
    TokenSendParams,
    UTXOSpendParams,
    WalletTx,
)
from mintlayer.wallet.types import Outpoint, OutpointSourceID, Timestamp, TxStats

_ZERO_OPTIONS = {"in_top_x_mb": None, "broadcast_to_mempool": None}


def test_outpoint_round_trip() -> None:
    outpoint = Outpoint(
        source_id=OutpointSourceID(type="Transaction", content={"tx_id": "beefcafe01"}),
        index=3,
    )
    assert Outpoint.from_json(outpoint.to_json()) == outpoint


def test_outpoint_source_id_block_reward_round_trip() -> None:
    source = OutpointSourceID(type="BlockReward", content={"block_id": "aabb0102"})
    assert OutpointSourceID.from_json(source.to_json()) == source


def _send_result(tx_id: str = "cafebabe") -> dict:
    return {
        "tx_id": tx_id,
        "fees": {"coins": {"atoms": "10000", "decimal": "0.0001"}, "tokens": {}},
        "broadcasted": True,
    }


def test_address_send(rpc_server) -> None:
    srv = rpc_server(result=_send_result())
    client = Client(srv.url)
    got = client.address_send(
        SendParams(account=0, address="tmltool1dest", amount=Amount(decimal="10.5"))
    )
    assert got == SendResult(
        tx_id="cafebabe",
        fees=FeesBreakdown(coins=Amount(atoms="10000", decimal="0.0001"), tokens={}),
        broadcasted=True,
    )
    assert srv.capture.method == "address_send"
    client.close()


@pytest.mark.parametrize("selected", [None, []], ids=["none", "empty_list"])
def test_address_send_selected_utxos_key_absent(rpc_server, selected) -> None:
    """None and [] both omit ``selected_utxos`` from the wire (omitempty)."""
    srv = rpc_server(result=_send_result())
    client = Client(srv.url)
    client.address_send(
        SendParams(
            account=0,
            address="tmltool1dest",
            amount=Amount(atoms="1000000000000"),
            selected_utxos=selected,
        )
    )
    assert srv.capture.method == "address_send"
    assert srv.capture.params == {
        "account": 0,
        "address": "tmltool1dest",
        "amount": {"atoms": "1000000000000"},
        "options": _ZERO_OPTIONS,
    }
    assert "selected_utxos" not in srv.capture.params
    client.close()


def test_address_send_selected_utxos_outpoint_shape(rpc_server) -> None:
    srv = rpc_server(result=_send_result())
    client = Client(srv.url)
    tx_id = "beefcafe01"
    client.address_send(
        SendParams(
            account=0,
            address="tmltool1dest",
            amount=Amount(atoms="1000000000000"),
            selected_utxos=[
                Outpoint(
                    source_id=OutpointSourceID(type="Transaction", content={"tx_id": tx_id}),
                    index=0,
                )
            ],
        )
    )
    assert srv.capture.params["selected_utxos"] == [
        {"source_id": {"type": "Transaction", "content": {"tx_id": tx_id}}, "index": 0}
    ]
    client.close()


def test_token_send(rpc_server) -> None:
    srv = rpc_server(
        result={"tx_id": "aabbccdd", "fees": {"coins": {}, "tokens": {}}, "broadcasted": True}
    )
    client = Client(srv.url)
    got = client.token_send(
        TokenSendParams(
            account=0,
            token_id="mytoken1abc",
            address="tmltool1dest",
            amount=Amount(decimal="100"),
        )
    )
    assert got.tx_id == "aabbccdd"
    assert got.broadcasted is True
    assert srv.capture.method == "token_send"
    assert srv.capture.params == {
        "account": 0,
        "token_id": "mytoken1abc",
        "address": "tmltool1dest",
        "amount": {"decimal": "100"},
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_sweep_spendable(rpc_server) -> None:
    srv = rpc_server(result=_send_result("sweep01"))
    client = Client(srv.url)
    got = client.sweep_spendable(
        SweepParams(account=0, destination_address="tmltool1dest", all=True)
    )
    assert got.tx_id == "sweep01"
    assert got.broadcasted is True
    assert srv.capture.method == "address_sweep_spendable"
    # from_addresses stays an explicit empty list on the wire.
    assert srv.capture.params == {
        "account": 0,
        "destination_address": "tmltool1dest",
        "from_addresses": [],
        "all": True,
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_spend_utxo(rpc_server) -> None:
    srv = rpc_server(result=_send_result("utxo01"))
    client = Client(srv.url)
    got = client.spend_utxo(
        UTXOSpendParams(
            account=0,
            utxo=Outpoint(
                source_id=OutpointSourceID(type="Transaction", content={"tx_id": "beefcafe01"}),
                index=1,
            ),
            output_address="tmltool1dest",
        )
    )
    assert got.tx_id == "utxo01"
    assert srv.capture.method == "utxo_spend"
    assert srv.capture.params == {
        "account": 0,
        "utxo": {
            "source_id": {"type": "Transaction", "content": {"tx_id": "beefcafe01"}},
            "index": 1,
        },
        "output_address": "tmltool1dest",
        "htlc_secret": None,
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_compose_transaction(rpc_server) -> None:
    srv = rpc_server(result={"hex": "deadbeef", "fees": {"coins": {"atoms": "5000"}, "tokens": {}}})
    client = Client(srv.url)
    got = client.compose_transaction(
        ComposeParams(outputs=[{"output": "raw"}], only_transaction=True)
    )
    assert got.hex == "deadbeef"
    assert got.fees == FeesBreakdown(coins=Amount(atoms="5000"), tokens={})
    assert srv.capture.method == "transaction_compose"
    assert srv.capture.params == {
        "inputs": [],
        "outputs": [{"output": "raw"}],
        "htlc_secrets": None,
        "only_transaction": True,
    }
    client.close()


def test_sign_raw_transaction(rpc_server) -> None:
    srv = rpc_server(result={"hex": "signed01", "current_signatures": []})
    client = Client(srv.url)
    got = client.sign_raw_transaction(0, "unsigned01")
    assert got == SignedTx(hex="signed01", current_signatures=[])
    assert srv.capture.method == "account_sign_raw_transaction"
    # The zero TxOptions shape is pinned on the wire.
    assert srv.capture.params == {
        "account": 0,
        "raw_tx": "unsigned01",
        "options": _ZERO_OPTIONS,
    }
    client.close()


def test_inspect_transaction_fees_null(rpc_server) -> None:
    srv = rpc_server(result={"stats": {"num_inputs": 2, "total_signatures": 2}, "fees": None})
    client = Client(srv.url)
    got = client.inspect_transaction("cafebabe")
    assert got.stats == TxStats(num_inputs=2, total_signatures=2)
    assert got.fees is None
    assert srv.capture.method == "transaction_inspect"
    assert srv.capture.params == {"transaction": "cafebabe"}
    client.close()


def test_inspect_transaction_with_fees(rpc_server) -> None:
    srv = rpc_server(
        result={
            "stats": {"num_inputs": 2, "total_signatures": 2},
            "fees": {"coins": {"atoms": "10000", "decimal": "0.0001"}, "tokens": {}},
        }
    )
    client = Client(srv.url)
    got = client.inspect_transaction("cafebabe")
    assert got.fees == FeesBreakdown(coins=Amount(atoms="10000", decimal="0.0001"), tokens={})
    client.close()


def test_submit_transaction(rpc_server) -> None:
    srv = rpc_server(result={"tx_id": "submitted01"})
    client = Client(srv.url)
    got = client.submit_transaction("cafebabe01020304")
    assert got == SubmitResult(tx_id="submitted01")
    assert srv.capture.method == "node_submit_transaction"
    # Trust policy is hardcoded to "Trusted" by the daemon route.
    assert srv.capture.params == {
        "tx": "cafebabe01020304",
        "do_not_store": False,
        "options": {"trust_policy": "Trusted"},
    }
    client.close()


def test_list_transactions_by_address(rpc_server) -> None:
    result = [{"id": "tx1", "height": 100, "timestamp": {"timestamp": 1700000000}}]
    srv = rpc_server(result=result)
    client = Client(srv.url)
    got = client.list_transactions_by_address(0, None, 20)
    assert got == [WalletTx(id="tx1", height=100, timestamp=Timestamp(timestamp=1700000000))]
    assert srv.capture.method == "transaction_list_by_address"
    assert srv.capture.params == {"account": 0, "address": None, "limit": 20}
    client.close()


def test_list_pending_transactions(rpc_server) -> None:
    srv = rpc_server(result=["tx1", "tx2"])
    client = Client(srv.url)
    assert client.list_pending_transactions(0) == ["tx1", "tx2"]
    assert srv.capture.method == "transaction_list_pending"
    assert srv.capture.params == {"account": 0}
    client.close()


def test_get_transaction_raw_passthrough(rpc_server) -> None:
    result = {"id": "tx1", "height": 100}
    srv = rpc_server(result=result)
    client = Client(srv.url)
    assert client.get_transaction(0, "tx1") == result
    assert srv.capture.method == "transaction_get"
    assert srv.capture.params == {"account": 0, "transaction_id": "tx1"}
    client.close()


def test_abandon_transaction(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.abandon_transaction(0, "tx1")
    assert srv.capture.method == "transaction_abandon"
    assert srv.capture.params == {"account": 0, "transaction_id": "tx1"}
    client.close()


def test_deposit_data(rpc_server) -> None:
    srv = rpc_server(result=_send_result("data01"))
    client = Client(srv.url)
    got = client.deposit_data(0, "68656c6c6f")
    assert got.tx_id == "data01"
    assert srv.capture.method == "address_deposit_data"
    assert srv.capture.params == {
        "account": 0,
        "data": "68656c6c6f",
        "options": _ZERO_OPTIONS,
    }
    client.close()
