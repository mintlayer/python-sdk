"""Tests for the p2p module methods.

Mirrors the "p2p module" section of go-sdk/node/client_test.go.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from mintlayer.node import BannedPeer, Client, PeerInfo, TrustPolicy
from mintlayer.node.p2p import _duration_to_wire

_LIST_BANNED_WIRE = '[["1.2.3.4",{"time":[1700000000,0]}]]'


def test_get_peer_count(rpc_server) -> None:
    srv = rpc_server(result=7)
    client = Client(srv.url)
    assert client.get_peer_count() == 7
    assert srv.capture.method == "p2p_get_peer_count"
    client.close()


def test_get_connected_peers(rpc_server) -> None:
    """PeerInfo decodes with a null ping_wait (optional fields absent/null)."""
    srv = rpc_server(
        result=[
            {
                "peer_id": 42,
                "address": "1.2.3.4:3031",
                "peer_role": "OutboundFullRelay",
                "ban_score": 0,
                "user_agent": "mintlayer-node/1.3.0",
                "software_version": "1.3.0",
                "ping_wait": None,
            }
        ]
    )
    client = Client(srv.url)
    peers = client.get_connected_peers()
    assert peers == [
        PeerInfo(
            peer_id=42,
            address="1.2.3.4:3031",
            peer_role="OutboundFullRelay",
            ban_score=0,
            user_agent="mintlayer-node/1.3.0",
            software_version="1.3.0",
            ping_wait=None,
        )
    ]
    assert len(peers) == 1
    assert peers[0].peer_id == 42
    assert peers[0].ping_wait is None
    assert srv.capture.method == "p2p_get_connected_peers"
    client.close()


def test_list_banned(rpc_server) -> None:
    """Wire format: [["addr", {"time": [secs, nanos]}], ...] (raw JSON result)."""
    srv = rpc_server(raw=_LIST_BANNED_WIRE)
    client = Client(srv.url)
    banned = client.list_banned()
    assert banned == [BannedPeer(address="1.2.3.4", ban_time=(1700000000, 0))]
    assert banned[0].address == "1.2.3.4"
    assert banned[0].ban_time == (1700000000, 0)
    assert banned[0].ban_time[0] == 1700000000
    assert srv.capture.method == "p2p_list_banned"
    client.close()


def test_ban_duration_wire_format(rpc_server) -> None:
    """Durations are sent as the daemon's two-element [seconds, nanos] array."""
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.ban("5.6.7.8", timedelta(hours=24)) is None
    assert srv.capture.method == "p2p_ban"
    duration = srv.capture.params["duration"]
    assert isinstance(duration, list)
    assert len(duration) == 2
    assert srv.capture.params == {"address": "5.6.7.8", "duration": [86400, 0]}
    client.close()


def test_ban_sub_second_duration(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    client.ban("5.6.7.8", timedelta(seconds=1, microseconds=500_000))
    assert srv.capture.params == {"address": "5.6.7.8", "duration": [1, 500000000]}
    client.close()


def test_duration_to_wire_rejects_negative_durations() -> None:
    """Negative durations fail closed before they can corrupt the wire form.

    Python normalises ``timedelta(seconds=-1)`` to ``(days=-1, seconds=86399)``;
    encoding that naively would send [86399, 0] (~a 24h ban) instead of -1s.
    """
    with pytest.raises(ValueError, match="must not be negative"):
        _duration_to_wire(timedelta(seconds=-1))
    with pytest.raises(ValueError, match="must not be negative"):
        _duration_to_wire(timedelta(days=-2))


@pytest.mark.parametrize(
    ("duration", "wire"),
    [
        pytest.param(timedelta(days=1), [86_400, 0], id="one_day"),
        pytest.param(timedelta(seconds=1), [1, 0], id="one_second"),
        pytest.param(timedelta(microseconds=1500), [0, 1_500_000], id="sub_second"),
    ],
)
def test_duration_to_wire_positive_durations(duration: timedelta, wire: list[int]) -> None:
    """Positive durations split into the daemon's [seconds, nanoseconds] pair."""
    assert _duration_to_wire(duration) == wire


def test_p2p_submit_transaction(rpc_server) -> None:
    srv = rpc_server(result=None)
    client = Client(srv.url)
    assert client.p2p_submit_transaction("cafebabe", TrustPolicy.UNTRUSTED) is None
    assert srv.capture.method == "p2p_submit_transaction"
    assert srv.capture.params == {
        "tx": "cafebabe",
        "options": {"trust_policy": "Untrusted"},
    }
    client.close()
