"""JSON-RPC client for the Mintlayer node daemon (mirrors go-sdk/node).

Default ports: 3030 (mainnet), 13030 (testnet). Errors from the daemon raise
:class:`RPCError` with a numeric ``code`` and ``message``.
"""

from __future__ import annotations

from requests import Session

from mintlayer._jsonrpc import JSONRPCClient, JSONRPCError, RPCError

from ._core import _NodeCore
from .chainstate import ChainstateMixin
from .mempool import MempoolMixin
from .node import NodeMixin
from .p2p import P2PMixin

__all__ = ["Client", "RPCError", "JSONRPCError"]


class Client(
    NodeMixin,
    ChainstateMixin,
    MempoolMixin,
    P2PMixin,
    _NodeCore,
):
    """JSON-RPC 2.0 client for the Mintlayer node daemon.

    Safe for concurrent use from multiple threads.
    """

    def __init__(
        self,
        endpoint: str,
        username: str = "",
        password: str = "",
        timeout: float = 30.0,
        session: Session | None = None,
    ) -> None:
        """Create a node client.

        ``endpoint`` is the base URL of the daemon (e.g.
        ``"http://127.0.0.1:3030"``); requests POST to it directly with no path
        appended. Basic auth is applied only when ``username`` is non-empty.
        """
        self._rpc = JSONRPCClient(
            endpoint=endpoint,
            username=username,
            password=password,
            timeout=timeout,
            session=session,
        )
