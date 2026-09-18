"""Node module methods (mirrors go-sdk/node/node.go)."""

from __future__ import annotations

from ._core import _NodeCore


class NodeMixin(_NodeCore):
    def node_version(self) -> str:
        """Return the node daemon version string."""
        return self._call_str("node_version", {})

    def node_shutdown(self) -> None:
        """Request a graceful node shutdown."""
        self._call_ignore("node_shutdown", {})
