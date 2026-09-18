"""Types for the indexer REST client (mirrors go-sdk/indexer/types.go).

Amounts carry both ``atoms`` and ``decimal`` as plain strings. Fields the
server serialises leniently (numbers-as-strings) are parsed via
:mod:`mintlayer.indexer.number`. Raw JSON passthroughs are typed ``Any``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from ._http import IndexerError
from .number import parse_per_thousand, parse_uint64

_T = TypeVar("_T")

__all__ = [
    "Amount",
    "Timestamp",
    "ChainTip",
    "GenesisInfo",
    "BlockHeader",
    "BlockBody",
    "Block",
    "Transaction",
    "MerklePath",
    "TokenBalance",
    "AddressInfo",
    "UTXOOutpoint",
    "UTXO",
    "DelegationInfo",
    "Pool",
    "Delegation",
    "PoolDelegation",
    "TokenInfo",
    "TokenTx",
    "NFTMetadata",
    "NFTInfo",
    "Order",
    "CoinStats",
    "PageOpts",
    "PoolListOpts",
]


@dataclass(frozen=True)
class Amount:
    """Coin/token amount in atoms and decimal form (both plain strings)."""

    atoms: str
    decimal: str

    @classmethod
    def from_json(cls, data: dict) -> Amount:
        # Required keys: a truncated payload must surface as IndexerError via
        # _safe_from_json, not silently decode to a zero-value Amount.
        return cls(atoms=data["atoms"], decimal=data["decimal"])


@dataclass(frozen=True)
class Timestamp:
    """Unix seconds."""

    timestamp: int

    @classmethod
    def from_json(cls, data: dict) -> Timestamp:
        return cls(timestamp=int(data["timestamp"]))


@dataclass(frozen=True)
class ChainTip:
    block_height: int
    block_id: str

    @classmethod
    def from_json(cls, data: dict) -> ChainTip:
        return cls(
            block_height=parse_uint64(data["block_height"]),
            block_id=data["block_id"],
        )


@dataclass(frozen=True)
class GenesisInfo:
    block_id: str
    genesis_message: str
    timestamp: Timestamp
    utxos: Any

    @classmethod
    def from_json(cls, data: dict) -> GenesisInfo:
        return cls(
            block_id=data["block_id"],
            genesis_message=data["genesis_message"],
            timestamp=Timestamp.from_json(data["timestamp"]),
            utxos=data.get("utxos"),
        )


@dataclass(frozen=True)
class BlockHeader:
    previous_block_id: str
    timestamp: Timestamp
    merkle_root: str
    witness_merkle_root: str
    consensus_data: Any

    @classmethod
    def from_json(cls, data: dict) -> BlockHeader:
        return cls(
            previous_block_id=data["previous_block_id"],
            timestamp=Timestamp.from_json(data["timestamp"]),
            merkle_root=data["merkle_root"],
            witness_merkle_root=data["witness_merkle_root"],
            consensus_data=data.get("consensus_data"),
        )


@dataclass(frozen=True)
class BlockBody:
    reward: Any
    transactions: list[Transaction]

    @classmethod
    def from_json(cls, data: dict) -> BlockBody:
        return cls(
            reward=data.get("reward"),
            transactions=[Transaction.from_json(t) for t in data.get("transactions") or []],
        )


@dataclass(frozen=True)
class Block:
    height: int
    header: BlockHeader
    body: BlockBody

    @classmethod
    def from_json(cls, data: dict) -> Block:
        return cls(
            height=parse_uint64(data["height"]),
            header=BlockHeader.from_json(data["header"]),
            body=BlockBody.from_json(data["body"]),
        )


@dataclass(frozen=True)
class Transaction:
    """Block ID / timestamp / confirmations are empty strings when unconfirmed."""

    id: str
    inputs: Any
    outputs: Any
    block_id: str
    timestamp: str
    confirmations: str

    @classmethod
    def from_json(cls, data: dict) -> Transaction:
        return cls(
            id=data["id"],
            inputs=data.get("inputs"),
            outputs=data.get("outputs"),
            block_id=data.get("block_id", ""),
            timestamp=data.get("timestamp", ""),
            confirmations=data.get("confirmations", ""),
        )


@dataclass(frozen=True)
class MerklePath:
    block_id: str
    transaction_index: int
    merkle_root: str
    path: list[str]

    @classmethod
    def from_json(cls, data: dict) -> MerklePath:
        return cls(
            block_id=data["block_id"],
            merkle_root=data["merkle_root"],
            transaction_index=parse_uint64(data["transaction_index"]),
            path=data.get("merkle_path") or [],
        )


@dataclass(frozen=True)
class TokenBalance:
    token_id: str
    amount: Amount

    @classmethod
    def from_json(cls, data: dict) -> TokenBalance:
        return cls(token_id=data["token_id"], amount=Amount.from_json(data["amount"]))


@dataclass(frozen=True)
class AddressInfo:
    coin_balance: Amount
    locked_coin_balance: Amount
    transaction_history: list[str]
    tokens: list[TokenBalance]

    @classmethod
    def from_json(cls, data: dict) -> AddressInfo:
        return cls(
            coin_balance=Amount.from_json(data["coin_balance"]),
            locked_coin_balance=Amount.from_json(data["locked_coin_balance"]),
            transaction_history=data.get("transaction_history") or [],
            tokens=[TokenBalance.from_json(t) for t in data.get("tokens") or []],
        )


@dataclass(frozen=True)
class UTXOOutpoint:
    source_id: str
    index: int

    @classmethod
    def from_json(cls, data: dict) -> UTXOOutpoint:
        return cls(
            source_id=data["source_id"],
            index=parse_uint64(data["index"]),
        )


@dataclass(frozen=True)
class UTXO:
    """Field/JSON-tag note: the output payload lives under the key ``utxo``."""

    outpoint: UTXOOutpoint
    output: Any

    @classmethod
    def from_json(cls, data: dict) -> UTXO:
        return cls(
            outpoint=UTXOOutpoint.from_json(data["outpoint"]),
            output=data.get("utxo"),
        )


@dataclass(frozen=True)
class DelegationInfo:
    """Address-scoped delegation (no creation height)."""

    delegation_id: str
    pool_id: str
    next_nonce: int
    spend_destination: str
    balance: Amount

    @classmethod
    def from_json(cls, data: dict) -> DelegationInfo:
        return cls(
            delegation_id=data["delegation_id"],
            pool_id=data["pool_id"],
            next_nonce=parse_uint64(data["next_nonce"]),
            spend_destination=data["spend_destination"],
            balance=Amount.from_json(data["balance"]),
        )


@dataclass(frozen=True)
class Pool:
    pool_id: str
    decommission_destination: str
    staker_balance: Amount
    margin_ratio_per_thousand: float
    cost_per_block: Amount
    vrf_public_key: str
    delegations_balance: Amount

    @classmethod
    def from_json(cls, data: dict) -> Pool:
        return cls(
            pool_id=data["pool_id"],
            decommission_destination=data["decommission_destination"],
            staker_balance=Amount.from_json(data["staker_balance"]),
            margin_ratio_per_thousand=parse_per_thousand(data["margin_ratio_per_thousand"]),
            cost_per_block=Amount.from_json(data["cost_per_block"]),
            vrf_public_key=data["vrf_public_key"],
            delegations_balance=Amount.from_json(data["delegations_balance"]),
        )


@dataclass(frozen=True)
class Delegation:
    delegation_id: str
    pool_id: str
    next_nonce: int
    spend_destination: str
    balance: Amount
    creation_block_height: int

    @classmethod
    def from_json(cls, data: dict) -> Delegation:
        return cls(
            delegation_id=data["delegation_id"],
            pool_id=data["pool_id"],
            next_nonce=parse_uint64(data["next_nonce"]),
            spend_destination=data["spend_destination"],
            balance=Amount.from_json(data["balance"]),
            creation_block_height=parse_uint64(data["creation_block_height"]),
        )


@dataclass(frozen=True)
class PoolDelegation:
    """Delegation as seen from a pool (no pool ID field)."""

    delegation_id: str
    next_nonce: int
    spend_destination: str
    balance: Amount
    creation_block_height: int

    @classmethod
    def from_json(cls, data: dict) -> PoolDelegation:
        return cls(
            delegation_id=data["delegation_id"],
            next_nonce=parse_uint64(data["next_nonce"]),
            spend_destination=data["spend_destination"],
            balance=Amount.from_json(data["balance"]),
            creation_block_height=parse_uint64(data["creation_block_height"]),
        )


@dataclass(frozen=True)
class TokenInfo:
    """Indexer token info.

    ``is_token_unfreezable`` is set only when frozen; ``is_token_freezable``
    only when not frozen (mirrors the Go pointer semantics).
    """

    authority: str
    is_locked: bool
    circulating_supply: Amount
    token_ticker: str
    metadata_uri: str
    number_of_decimals: int
    total_supply: Any
    frozen: bool
    is_token_unfreezable: bool | None
    is_token_freezable: bool | None
    next_nonce: int

    @classmethod
    def from_json(cls, data: dict) -> TokenInfo:
        return cls(
            authority=data["authority"],
            is_locked=data["is_locked"],
            circulating_supply=Amount.from_json(data["circulating_supply"]),
            token_ticker=data["token_ticker"],
            metadata_uri=data["metadata_uri"],
            number_of_decimals=parse_uint64(data["number_of_decimals"]),
            total_supply=data.get("total_supply"),
            frozen=data["frozen"],
            is_token_unfreezable=data.get("is_token_unfreezable"),
            is_token_freezable=data.get("is_token_freezable"),
            next_nonce=parse_uint64(data["next_nonce"]),
        )


@dataclass(frozen=True)
class TokenTx:
    tx_global_index: int
    tx_id: str

    @classmethod
    def from_json(cls, data: dict) -> TokenTx:
        return cls(
            tx_global_index=parse_uint64(data["tx_global_index"]),
            tx_id=data["tx_id"],
        )


@dataclass(frozen=True)
class NFTMetadata:
    creator: str | None
    name: str
    description: str
    ticker: str
    icon_uri: str | None
    additional_metadata_uri: str | None
    media_uri: str | None
    media_hash: str

    @classmethod
    def from_json(cls, data: dict) -> NFTMetadata:
        return cls(
            creator=data.get("creator"),
            name=data["name"],
            description=data["description"],
            ticker=data["ticker"],
            icon_uri=data.get("icon_uri"),
            additional_metadata_uri=data.get("additional_metadata_uri"),
            media_uri=data.get("media_uri"),
            media_hash=data["media_hash"],
        )


@dataclass(frozen=True)
class NFTInfo:
    owner: str
    token_id: str
    metadata: NFTMetadata

    @classmethod
    def from_json(cls, data: dict) -> NFTInfo:
        return cls(
            owner=data["owner"],
            token_id=data["token_id"],
            metadata=NFTMetadata.from_json(data["metadata"]),
        )


@dataclass(frozen=True)
class Order:
    order_id: str
    conclude_destination: str
    give_currency: Any
    initially_given: Amount
    give_balance: Amount
    ask_currency: Any
    initially_asked: Amount
    ask_balance: Amount
    nonce: int

    @classmethod
    def from_json(cls, data: dict) -> Order:
        return cls(
            order_id=data["order_id"],
            conclude_destination=data["conclude_destination"],
            give_currency=data.get("give_currency"),
            initially_given=Amount.from_json(data["initially_given"]),
            give_balance=Amount.from_json(data["give_balance"]),
            ask_currency=data.get("ask_currency"),
            initially_asked=Amount.from_json(data["initially_asked"]),
            ask_balance=Amount.from_json(data["ask_balance"]),
            nonce=parse_uint64(data["nonce"]),
        )


@dataclass(frozen=True)
class CoinStats:
    circulating_supply: Amount
    preminted: Amount
    burned: Amount
    staked: Amount

    @classmethod
    def from_json(cls, data: dict) -> CoinStats:
        return cls(
            circulating_supply=Amount.from_json(data["circulating_supply"]),
            preminted=Amount.from_json(data["preminted"]),
            burned=Amount.from_json(data["burned"]),
            staked=Amount.from_json(data["staked"]),
        )


@dataclass(frozen=True)
class PageOpts:
    """Pagination; zero values use the server defaults (offset=0, items=10)."""

    offset: int = 0
    items: int = 0

    def query(self) -> dict[str, Any]:
        q: dict[str, Any] = {}
        if self.offset > 0:
            q["offset"] = self.offset
        if self.items > 0:
            q["items"] = self.items
        return q


@dataclass(frozen=True)
class PoolListOpts:
    """Pool listing options: pagination plus an optional sort order.

    ``sort`` is ``"by_height"`` (default, newest first) or ``"by_pledge"``
    (largest staker balance first); omitted when empty.
    """

    offset: int = 0
    items: int = 0
    sort: str = ""

    def query(self) -> dict[str, Any]:
        q = PageOpts(offset=self.offset, items=self.items).query()
        if self.sort:
            q["sort"] = self.sort
        return q


def _safe_from_json(cls: type[_T]) -> classmethod:
    """Wrap a from_json classmethod so malformed payloads raise IndexerError."""
    original: Callable[[type[_T], Any], _T] = cls.from_json.__func__  # type: ignore[attr-defined]

    def from_json(cls_: type[_T], data: Any) -> _T:
        try:
            return original(cls_, data)
        except IndexerError:
            raise
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise IndexerError(f"{cls_.__name__}: malformed payload ({exc!r})") from exc

    return classmethod(from_json)


for _cls in (
    Amount,
    Timestamp,
    ChainTip,
    GenesisInfo,
    BlockHeader,
    BlockBody,
    Block,
    Transaction,
    MerklePath,
    TokenBalance,
    AddressInfo,
    UTXOOutpoint,
    UTXO,
    DelegationInfo,
    Pool,
    Delegation,
    PoolDelegation,
    TokenInfo,
    TokenTx,
    NFTMetadata,
    NFTInfo,
    Order,
    CoinStats,
):
    _cls.from_json = _safe_from_json(_cls)  # type: ignore[assignment,method-assign]
