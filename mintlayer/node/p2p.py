"""P2P methods (mirrors go-sdk/node/p2p.go)."""

from __future__ import annotations

from datetime import timedelta

from ._core import _NodeCore
from .types import BannedPeer, PeerInfo, TrustPolicy
from .types import policy_value as _policy_value


def _duration_to_wire(duration: timedelta) -> list[int]:
    """Split a duration into the daemon's [seconds, nanoseconds] wire form."""
    secs = duration.days * 86_400 + duration.seconds
    nanos = duration.microseconds * 1_000
    return [secs, nanos]


class P2PMixin(_NodeCore):
    def get_peer_count(self) -> int:
        """Return the number of connected peers."""
        return self._call_int("p2p_get_peer_count", {})

    def get_connected_peers(self) -> list[PeerInfo]:
        """Return info about connected peers."""
        data = self._call("p2p_get_connected_peers", {})
        return [PeerInfo.from_json(item) for item in data or []]

    def get_bind_addresses(self) -> list[str]:
        """Return the node's bind addresses."""
        return self._call_str_list("p2p_get_bind_addresses", {})

    def add_reserved_node(self, addr: str) -> None:
        """Add a reserved node (host:port)."""
        self._call_ignore("p2p_add_reserved_node", {"addr": addr})

    def remove_reserved_node(self, addr: str) -> None:
        """Remove a reserved node (host:port)."""
        self._call_ignore("p2p_remove_reserved_node", {"addr": addr})

    def connect(self, addr: str) -> None:
        """Connect to a peer (host:port)."""
        self._call_ignore("p2p_connect", {"addr": addr})

    def disconnect(self, peer_id: int) -> None:
        """Disconnect the peer with the given ID."""
        self._call_ignore("p2p_disconnect", {"peer_id": peer_id})

    def list_banned(self) -> list[BannedPeer]:
        """Return banned addresses with their ban expiry times."""
        data = self._call("p2p_list_banned", {})
        return [BannedPeer.from_json(item) for item in data or []]

    def ban(self, address: str, duration: timedelta) -> None:
        """Ban an address for the given duration."""
        self._call_ignore("p2p_ban", {"address": address, "duration": _duration_to_wire(duration)})

    def unban(self, address: str) -> None:
        """Remove an address ban."""
        self._call_ignore("p2p_unban", {"address": address})

    def p2p_submit_transaction(self, tx_hex: str, trust_policy: TrustPolicy | str) -> None:
        """Submit a transaction to the mempool AND broadcast it via P2P."""
        self._call_ignore(
            "p2p_submit_transaction",
            {"tx": tx_hex, "options": {"trust_policy": _policy_value(trust_policy)}},
        )
