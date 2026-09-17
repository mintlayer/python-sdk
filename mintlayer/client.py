"""Top-level Mintlayer SDK client (mirrors go-sdk/client.go).

Constructs only the sub-clients whose URL is configured, wires the WASM
cryptography runtime lazily via :meth:`Client.init_wasm`, and re-exports the
common types so callers importing just ``mintlayer`` get the full surface.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from .indexer import Client as IndexerClient
from .node import Client as NodeClient
from .wallet import Client as WalletClient
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
from .wasm import (
    Client as WASMClient,
)

__all__ = [
    "Config",
    "Client",
    # re-exports (mirrors the Go SDK's convenience aliases)
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


@dataclass(frozen=True)
class Config:
    """Top-level SDK configuration.

    Only sub-clients whose URL field is non-empty are constructed.
    ``password`` is redacted from :func:`repr` to keep credentials out of logs.
    """

    node_url: str = ""
    indexer_url: str = ""
    wallet_url: str = ""
    username: str = ""
    password: str = field(default="", repr=False)
    timeout: float = 30.0

    def __repr__(self) -> str:
        return (
            f"Config(node_url={self.node_url!r}, indexer_url={self.indexer_url!r}, "
            f"wallet_url={self.wallet_url!r}, username={self.username!r}, "
            f"password='***', timeout={self.timeout!r})"
        )


class Client:
    """The top-level Mintlayer SDK client.

    ``node``, ``indexer`` and ``wallet`` are ``None`` when their URL was not
    set in the :class:`Config`; ``wasm`` is ``None`` until
    :meth:`init_wasm` is called (~400 ms one-time cost).
    """

    def __init__(self, cfg: Config) -> None:
        self._mu = threading.Lock()
        self._wasm: WASMClient | None = None

        self.node: NodeClient | None = None
        if cfg.node_url:
            self.node = NodeClient(
                cfg.node_url,
                username=cfg.username,
                password=cfg.password,
                timeout=cfg.timeout,
            )

        self.indexer: IndexerClient | None = None
        if cfg.indexer_url:
            self.indexer = IndexerClient(cfg.indexer_url, timeout=cfg.timeout)

        self.wallet: WalletClient | None = None
        if cfg.wallet_url:
            self.wallet = WalletClient(
                cfg.wallet_url,
                username=cfg.username,
                password=cfg.password,
                timeout=cfg.timeout,
            )

    def init_wasm(self) -> None:
        """Initialise the embedded WASM cryptography runtime (~400 ms).

        Subsequent calls are no-ops. Safe for concurrent use.
        """
        with self._mu:
            if self._wasm is None:
                self._wasm = WASMClient()

    @property
    def wasm(self) -> WASMClient:
        """The WASM cryptography client; :meth:`init_wasm` must be called first."""
        if self._wasm is None:
            raise WasmError("mintlayer: init_wasm() must be called before using client.wasm")
        return self._wasm

    def close(self) -> None:
        """Release WASM resources and close sessions owned by sub-clients."""
        with self._mu:
            if self.node is not None:
                self.node.close()
            if self.indexer is not None:
                self.indexer.close()
            if self.wallet is not None:
                self.wallet.close()
            if self._wasm is not None:
                self._wasm.close()
                self._wasm = None

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
