"""REST client for the Mintlayer indexer.

Mirrors go-sdk/indexer (Go package ``indexer``). Default port: 3000.
All paths are relative to ``/api/v2``.

    from mintlayer.indexer import Client

    c = Client("http://127.0.0.1:3000")
    tip = c.get_tip()
    print(tip.block_height, tip.block_id)
"""

from __future__ import annotations

import requests

from ._http import HTTPError, IndexerError, IndexerHTTP
from .address import AddressMixin
from .block import BlockMixin
from .chain import ChainMixin
from .delegation import DelegationMixin
from .order import OrderMixin
from .pool import PoolMixin
from .statistics import StatisticsMixin
from .token import TokenMixin
from .transaction import TransactionMixin
from .types import (
    UTXO,
    AddressInfo,
    Amount,
    Block,
    BlockHeader,
    ChainTip,
    CoinStats,
    Delegation,
    DelegationInfo,
    GenesisInfo,
    MerklePath,
    NFTInfo,
    NFTMetadata,
    Order,
    PageOpts,
    Pool,
    PoolDelegation,
    PoolListOpts,
    Timestamp,
    TokenBalance,
    TokenInfo,
    TokenTx,
    Transaction,
    UTXOOutpoint,
)

__all__ = [
    "Client",
    "HTTPError",
    "IndexerError",
    "Amount",
    "AddressInfo",
    "Block",
    "BlockHeader",
    "ChainTip",
    "CoinStats",
    "Delegation",
    "DelegationInfo",
    "GenesisInfo",
    "MerklePath",
    "Timestamp",
    "NFTInfo",
    "NFTMetadata",
    "Order",
    "PageOpts",
    "Pool",
    "PoolDelegation",
    "PoolListOpts",
    "TokenBalance",
    "TokenInfo",
    "TokenTx",
    "Transaction",
    "UTXO",
    "UTXOOutpoint",
]


class Client(
    ChainMixin,
    BlockMixin,
    TransactionMixin,
    AddressMixin,
    DelegationMixin,
    PoolMixin,
    TokenMixin,
    OrderMixin,
    StatisticsMixin,
):
    """REST client for the indexer (api-web-server).

    Safe for concurrent use from multiple threads. Any HTTP status >= 400
    raises :class:`HTTPError`.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        """Create an indexer client; trailing slashes on ``base_url`` are trimmed."""
        IndexerHTTP.__init__(self, base_url=base_url, timeout=timeout, session=session)

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
