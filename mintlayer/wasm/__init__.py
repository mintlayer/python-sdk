"""Mintlayer WASM cryptography and transaction-building client.

Mirrors go-sdk/wasm (Go package ``mintlayer``). Instantiates the embedded
wasm-bindgen module via wasmtime and exposes key derivation, address encoding,
transaction building, signing and fee queries.
"""

from __future__ import annotations

from .client import Client
from .types import (
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

# Convenience aliases matching the Go SDK's constant names.
MAINNET = Network.MAINNET
TESTNET = Network.TESTNET
REGTEST = Network.REGTEST
SIGNET = Network.SIGNET

SIGHASH_ALL = SignatureHashType.SIGHASH_ALL
SIGHASH_NONE = SignatureHashType.SIGHASH_NONE
SIGHASH_SINGLE = SignatureHashType.SIGHASH_SINGLE
SIGHASH_ANYONECANPAY = SignatureHashType.SIGHASH_ANYONECANPAY

SOURCE_TRANSACTION = SourceId.SOURCE_TRANSACTION
SOURCE_BLOCK_REWARD = SourceId.SOURCE_BLOCK_REWARD

__all__ = [
    "Client",
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
    "OrderInfo",
    "PoolInfo",
    "TxAdditionalInfo",
    "WasmError",
]
