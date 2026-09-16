"""Types shared across the WASM cryptography client.

Mirrors go-sdk/wasm/types.go: enums are passed to WASM as their integer
discriminant, and JSON shapes match the Rust serde structures exactly.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class WasmError(Exception):
    """Error raised by WASM operations. Messages are prefixed with ``mintlayer: ``."""


class Network(enum.IntEnum):
    """Mintlayer blockchain network."""

    MAINNET = 0
    TESTNET = 1
    REGTEST = 2
    SIGNET = 3


class SignatureHashType(enum.IntEnum):
    """Controls which parts of a transaction are covered by a signature."""

    SIGHASH_ALL = 0
    SIGHASH_NONE = 1
    SIGHASH_SINGLE = 2
    SIGHASH_ANYONECANPAY = 3


class SourceId(enum.IntEnum):
    """Whether a UTXO comes from a transaction output or a block reward."""

    SOURCE_TRANSACTION = 0
    SOURCE_BLOCK_REWARD = 1


class TotalSupply(enum.IntEnum):
    """Supply policy of a fungible token."""

    LOCKABLE = 0
    UNLIMITED = 1
    FIXED = 2


class FreezableToken(enum.IntEnum):
    """Whether a token can be frozen after issuance."""

    NO = 0
    YES = 1


class TokenUnfreezable(enum.IntEnum):
    """Whether a frozen token can later be unfrozen."""

    NO = 0
    YES = 1


class CurrencyAmountKind(enum.IntEnum):
    """Selects the coins/tokens variant of a SimpleCurrencyAmount."""

    COINS = 0
    TOKENS = 1


@dataclass(frozen=True)
class Amount:
    """A coin or token quantity as a decimal atom count.

    Atoms are the smallest indivisible unit; 1 ML = 100000000000 (1e11) atoms.
    """

    atoms: str

    @classmethod
    def from_atoms(cls, atoms: str) -> Amount:
        """Create an Amount from a decimal atom string (e.g. ``"100000000000"``)."""
        return cls(atoms=atoms)

    @classmethod
    def zero(cls) -> Amount:
        """An Amount representing zero atoms."""
        return cls(atoms="0")

    def to_json_value(self) -> dict:
        return {"atoms": self.atoms}

    def __str__(self) -> str:
        return self.atoms


@dataclass(frozen=True)
class SimpleCurrencyAmount:
    """Ask/give balances inside TxAdditionalInfo.

    Serialised as the externally tagged CurrencyAmount enum:

    * ``{"coins":{"atoms":"<atoms>"}}``
    * ``{"tokens":{"amount":{"atoms":"<atoms>"},"token_id":"<id>"}}``
    """

    atoms: str
    kind: CurrencyAmountKind = CurrencyAmountKind.COINS
    token_id: str | None = None

    @classmethod
    def coins(cls, atoms: str) -> SimpleCurrencyAmount:
        return cls(atoms=atoms, kind=CurrencyAmountKind.COINS, token_id=None)

    @classmethod
    def tokens(cls, atoms: str, token_id: str) -> SimpleCurrencyAmount:
        return cls(atoms=atoms, kind=CurrencyAmountKind.TOKENS, token_id=token_id)

    def to_json_value(self) -> dict:
        if self.kind == CurrencyAmountKind.TOKENS:
            return {
                "tokens": {
                    "amount": {"atoms": self.atoms},
                    "token_id": self.token_id,
                }
            }
        return {"coins": {"atoms": self.atoms}}


@dataclass(frozen=True)
class OrderBalance:
    """One side of a DEX order's remaining balance.

    Serialised with the redundant-but-required shape
    ``{"atoms":"...","amount":{"atoms":"..."},"token_id":null|"..."}``.
    """

    atoms: str
    token_id: str | None = None

    def to_json_value(self) -> dict:
        return {
            "atoms": self.atoms,
            "amount": {"atoms": self.atoms},
            "token_id": self.token_id,
        }


@dataclass(frozen=True)
class PoolInfo:
    """Pool-related data required for signing pool UTXOs."""

    staker_balance: Amount

    def to_json_value(self) -> dict:
        return {"staker_balance": self.staker_balance.to_json_value()}


@dataclass(frozen=True)
class OrderInfo:
    """DEX order data required for signing order UTXOs."""

    initially_asked: SimpleCurrencyAmount
    initially_given: SimpleCurrencyAmount
    ask_balance: OrderBalance
    give_balance: OrderBalance

    def to_json_value(self) -> dict:
        return {
            "initially_asked": self.initially_asked.to_json_value(),
            "initially_given": self.initially_given.to_json_value(),
            "ask_balance": self.ask_balance.to_json_value(),
            "give_balance": self.give_balance.to_json_value(),
        }


@dataclass
class TxAdditionalInfo:
    """Out-of-band pool/order state needed when signing pool or order UTXOs.

    Maps are keyed by the bech32m pool/order ID. An empty dict serialises as an
    empty JSON object (no pool/order data); the WASM module rejects ``null``
    maps, so defaults are empty dicts rather than ``None``.
    """

    pool_info: dict[str, PoolInfo] = field(default_factory=dict)
    order_info: dict[str, OrderInfo] = field(default_factory=dict)

    def to_json_value(self) -> dict:
        return {
            "pool_info": {k: v.to_json_value() for k, v in self.pool_info.items()},
            "order_info": {k: v.to_json_value() for k, v in self.order_info.items()},
        }
