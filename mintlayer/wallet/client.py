"""JSON-RPC client for the Mintlayer wallet daemon (mirrors go-sdk/wallet)."""

from __future__ import annotations

import requests

from mintlayer._jsonrpc import JSONRPCClient, JSONRPCError, RPCError

from ._core import _WalletCore
from .management import ManagementMixin
from .orders import OrdersMixin
from .staking import StakingMixin
from .tokens import TokensMixin
from .transactions import TransactionsMixin

__all__ = ["Client", "RPCError", "JSONRPCError"]


class Client(
    ManagementMixin,
    TransactionsMixin,
    TokensMixin,
    StakingMixin,
    OrdersMixin,
    _WalletCore,
):
    """JSON-RPC 2.0 client for the wallet-rpc-daemon.

    Default ports: 3034 (mainnet), 13034 (testnet). Safe for concurrent use
    from multiple threads.
    """

    def __init__(
        self,
        endpoint: str,
        username: str = "",
        password: str = "",
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        """Create a wallet client; requests POST directly to ``endpoint``.

        Basic auth is applied only when ``username`` is non-empty. Per-call
        cancellation is not supported; use ``timeout`` for deadlines.
        """
        self._rpc = JSONRPCClient(
            endpoint=endpoint,
            username=username,
            password=password,
            timeout=timeout,
            session=session,
        )

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
