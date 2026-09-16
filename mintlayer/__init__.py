"""Mintlayer Python SDK.

A Python SDK for the Mintlayer blockchain, ported from the
`Mintlayer Go SDK <https://github.com/mintlayer/go-sdk>`_.

    import mintlayer

    client = mintlayer.Client(mintlayer.Config(
        node_url="http://127.0.0.1:3030",
        indexer_url="http://127.0.0.1:3000",
        wallet_url="http://127.0.0.1:3034",
    ))

    tip = client.indexer.get_tip()
    client.init_wasm()
    priv = client.wasm.make_private_key()

The four sub-clients are also importable directly:
``mintlayer.node``, ``mintlayer.indexer``, ``mintlayer.wallet`` and
``mintlayer.wasm``.
"""

from __future__ import annotations

from . import indexer, node, wallet, wasm
from .client import Client, Config
from .wasm import (
    MAINNET,
    REGTEST,
    SIGHASH_ALL,
    SIGHASH_ANYONECANPAY,
    SIGHASH_NONE,
    SIGHASH_SINGLE,
    SIGNET,
    SOURCE_BLOCK_REWARD,
    SOURCE_TRANSACTION,
    TESTNET,
    Amount,
    CurrencyAmountKind,
    FreezableToken,
    Network,
    OrderBalance,
    OrderInfo,
    PoolInfo,
    SignatureHashType,
    SimpleCurrencyAmount,
    SourceId,
    TokenUnfreezable,
    TotalSupply,
    TxAdditionalInfo,
    WasmError,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Client",
    "Config",
    "node",
    "indexer",
    "wallet",
    "wasm",
    # convenience re-exports (mirrors the Go SDK root package)
    "Amount",
    "Network",
    "MAINNET",
    "TESTNET",
    "REGTEST",
    "SIGNET",
    "SignatureHashType",
    "SIGHASH_ALL",
    "SIGHASH_NONE",
    "SIGHASH_SINGLE",
    "SIGHASH_ANYONECANPAY",
    "SourceId",
    "SOURCE_TRANSACTION",
    "SOURCE_BLOCK_REWARD",
    "TotalSupply",
    "FreezableToken",
    "TokenUnfreezable",
    "CurrencyAmountKind",
    "SimpleCurrencyAmount",
    "OrderBalance",
    "PoolInfo",
    "OrderInfo",
    "TxAdditionalInfo",
    "WasmError",
]
