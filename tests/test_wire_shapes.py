"""Wire-shape tests for node client methods lacking dedicated coverage.

Pins the exact RPC method name and params dict sent on the wire for the
chainstate/p2p methods without their own request-shape assertion elsewhere,
mirroring the request-shape checks of go-sdk/node/client_test.go.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from mintlayer.node import Client

_WIRE_CASES = [
    pytest.param(lambda c: c.get_block("aa"), "chainstate_get_block", {"id": "aa"}, id="get_block"),
    pytest.param(
        lambda c: c.get_block_json("aa"),
        "chainstate_get_block_json",
        {"id": "aa"},
        id="get_block_json",
    ),
    pytest.param(
        lambda c: c.block_height_in_main_chain("bb"),
        "chainstate_block_height_in_main_chain",
        {"block_id": "bb"},
        id="block_height_in_main_chain",
    ),
    pytest.param(
        lambda c: c.get_mainchain_blocks(1, 5),
        "chainstate_get_mainchain_blocks",
        {"from": 1, "max_count": 5},
        id="get_mainchain_blocks",
    ),
    pytest.param(
        lambda c: c.staker_balance("pool1"),
        "chainstate_staker_balance",
        {"pool_address": "pool1"},
        id="staker_balance",
    ),
    pytest.param(
        lambda c: c.pool_decommission_destination("pool1"),
        "chainstate_pool_decommission_destination",
        {"pool_address": "pool1"},
        id="pool_decommission_destination",
    ),
    pytest.param(
        lambda c: c.delegation_share("pool1", "addr1"),
        "chainstate_delegation_share",
        {"pool_address": "pool1", "delegation_address": "addr1"},
        id="delegation_share",
    ),
    pytest.param(
        lambda c: c.token_info("t1"),
        "chainstate_token_info",
        {"token_id": "t1"},
        id="token_info",
    ),
    pytest.param(
        lambda c: c.tokens_info(["t1", "t2"]),
        "chainstate_tokens_info",
        {"token_ids": ["t1", "t2"]},
        id="tokens_info",
    ),
    pytest.param(
        lambda c: c.submit_block("c0ffee"),
        "chainstate_submit_block",
        {"block_hex": "c0ffee"},
        id="submit_block",
    ),
    pytest.param(
        lambda c: c.get_bind_addresses(),
        "p2p_get_bind_addresses",
        {},
        id="get_bind_addresses",
    ),
    pytest.param(
        lambda c: c.add_reserved_node("h:1"),
        "p2p_add_reserved_node",
        {"addr": "h:1"},
        id="add_reserved_node",
    ),
    pytest.param(
        lambda c: c.remove_reserved_node("h:1"),
        "p2p_remove_reserved_node",
        {"addr": "h:1"},
        id="remove_reserved_node",
    ),
    pytest.param(
        lambda c: c.connect("h:1"),
        "p2p_connect",
        {"addr": "h:1"},
        id="connect",
    ),
    pytest.param(
        lambda c: c.disconnect(7),
        "p2p_disconnect",
        {"peer_id": 7},
        id="disconnect",
    ),
    pytest.param(
        lambda c: c.unban("1.2.3.4"),
        "p2p_unban",
        {"address": "1.2.3.4"},
        id="unban",
    ),
]


@pytest.mark.parametrize(("invoke", "rpc_method", "expected_params"), _WIRE_CASES)
def test_method_wire_shapes(
    rpc_server,
    invoke: Callable[[Client], object],
    rpc_method: str,
    expected_params: dict,
) -> None:
    """Each method posts its exact RPC method name and params object.

    The canned server answers JSON null, which every covered method tolerates
    (optional -> None, void -> None, list -> [], raw decode -> None).
    """
    srv = rpc_server(result=None)
    client = Client(srv.url)
    invoke(client)
    assert srv.capture.method == rpc_method
    assert srv.capture.params == expected_params
    client.close()
