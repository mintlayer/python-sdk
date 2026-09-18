"""JSON-RPC client for the Mintlayer node daemon.

Mirrors go-sdk/node (Go package ``node``). Default ports: 3030 (mainnet),
13030 (testnet).

    from mintlayer.node import Client

    c = Client("http://127.0.0.1:3030")
    print(c.best_block_height())
"""

from __future__ import annotations

from mintlayer._jsonrpc import JSONRPCError

from .client import Client, RPCError
from .types import (
    Amount,
    BannedPeer,
    ChainstateInfo,
    Currency,
    FeeRate,
    FeeRatePoint,
    MempoolTx,
    OrderInfo,
    Outpoint,
    OutpointSourceID,
    PeerInfo,
    Timestamp,
    TokenInfo,
    TrustPolicy,
    block_source_content,
    tx_source_content,
)

__all__ = [
    "Client",
    "RPCError",
    "JSONRPCError",
    "Amount",
    "Timestamp",
    "ChainstateInfo",
    "OutpointSourceID",
    "Outpoint",
    "TokenInfo",
    "OrderInfo",
    "Currency",
    "TrustPolicy",
    "MempoolTx",
    "FeeRate",
    "FeeRatePoint",
    "PeerInfo",
    "BannedPeer",
    "tx_source_content",
    "block_source_content",
]
