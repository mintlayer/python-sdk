"""Types for the node JSON-RPC client (mirrors go-sdk/node/types.go).

Amounts are decimal atom strings (1 ML = 1e11 atoms) — never JSON numbers.
Tagged unions (``OutpointSourceID``, ``TokenInfo``) keep their ``content`` as
raw decoded JSON. Custom wire shapes (``FeeRatePoint``, ``BannedPeer``) use
tuple encodings decoded in ``from_json``.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any


class TrustPolicy(str, enum.Enum):
    """Mempool submission trust policy."""

    TRUSTED = "Trusted"
    UNTRUSTED = "Untrusted"


def policy_value(trust_policy: TrustPolicy | str) -> str:
    """Normalise a TrustPolicy enum or plain string to its wire value."""
    if isinstance(trust_policy, TrustPolicy):
        return trust_policy.value
    return TrustPolicy(trust_policy).value


@dataclass(frozen=True)
class Amount:
    """A coin or token quantity as a decimal atom string."""

    atoms: str

    @classmethod
    def from_json(cls, data: Any) -> Amount:
        if not isinstance(data, dict) or not isinstance(data.get("atoms"), str):
            # "atoms" must be a decimal string; a JSON number would silently
            # corrupt round-trips (the wire contract is strings only).
            raise ValueError(f"invalid amount payload: {data!r}")
        return cls(atoms=data["atoms"])

    def to_json(self) -> dict:
        return {"atoms": self.atoms}


@dataclass(frozen=True)
class Timestamp:
    """Unix seconds."""

    timestamp: int

    @classmethod
    def from_json(cls, data: Any) -> Timestamp:
        return cls(timestamp=int(data["timestamp"]))


@dataclass(frozen=True)
class ChainstateInfo:
    best_block_height: int
    best_block_id: str
    best_block_timestamp: Timestamp
    median_time: Timestamp
    is_initial_block_download: bool

    @classmethod
    def from_json(cls, data: dict) -> ChainstateInfo:
        return cls(
            best_block_height=data["best_block_height"],
            best_block_id=data["best_block_id"],
            best_block_timestamp=Timestamp.from_json(data["best_block_timestamp"]),
            median_time=Timestamp.from_json(data["median_time"]),
            is_initial_block_download=data["is_initial_block_download"],
        )


@dataclass
class OutpointSourceID:
    """Tagged union: ``type`` is ``"Transaction"`` or ``"BlockReward"``.

    ``content`` is raw JSON: ``{"tx_id": "<hex>"}`` or ``{"block_id": "<hex>"}``
    (see :func:`tx_source_content` / :func:`block_source_content`). Mirrors the
    Go struct's missing ``omitempty``: an unset content serialises as ``null``.
    """

    type: str
    content: Any = None

    def to_json(self) -> dict:
        return {"type": self.type, "content": self.content}

    @classmethod
    def from_json(cls, data: dict) -> OutpointSourceID:
        return cls(type=data["type"], content=data.get("content"))


def tx_source_content(tx_id: str) -> dict:
    """Content payload for a transaction outpoint source."""
    return {"tx_id": tx_id}


def block_source_content(block_id: str) -> dict:
    """Content payload for a block-reward outpoint source."""
    return {"block_id": block_id}


@dataclass(frozen=True)
class Outpoint:
    source_id: OutpointSourceID
    index: int

    def to_json(self) -> dict:
        return {"source_id": self.source_id.to_json(), "index": self.index}


@dataclass
class TokenInfo:
    """Tagged union: ``type`` is ``"FungibleToken"`` or ``"NonFungibleToken"``.

    ``content`` is left as raw decoded JSON.
    """

    type: str
    content: Any = None

    @classmethod
    def from_json(cls, data: dict) -> TokenInfo:
        return cls(type=data["type"], content=data.get("content"))


@dataclass
class OrderInfo:
    """Node-side order info.

    Note: ``nonce`` is ``None`` for active orders (the daemon sends ``null``),
    fixing a known Go SDK incompatibility.
    """

    conclude_key: str
    initially_asked: Any
    initially_given: Any
    ask_balance: Amount
    give_balance: Amount
    nonce: int | None
    is_frozen: bool

    @classmethod
    def from_json(cls, data: dict) -> OrderInfo:
        return cls(
            conclude_key=data["conclude_key"],
            initially_asked=data.get("initially_asked"),
            initially_given=data.get("initially_given"),
            ask_balance=Amount.from_json(data["ask_balance"]),
            give_balance=Amount.from_json(data["give_balance"]),
            nonce=data.get("nonce"),
            is_frozen=data["is_frozen"],
        )


@dataclass(frozen=True)
class Currency:
    """Tagged union query parameter: ``"Coin"`` or ``"Token"``.

    ``content`` carries the bech32 token ID for tokens and is omitted for coins
    (mirrors the Go struct's ``omitempty``).
    """

    type: str
    content: str | None = None

    def to_json(self) -> dict:
        out: dict = {"type": self.type}
        if self.content is not None:
            out["content"] = self.content
        return out

    @classmethod
    def coin(cls) -> Currency:
        return cls(type="Coin")

    @classmethod
    def token(cls, token_id: str) -> Currency:
        return cls(type="Token", content=token_id)


@dataclass(frozen=True)
class MempoolTx:
    id: str
    status: str
    transaction: str

    @classmethod
    def from_json(cls, data: dict) -> MempoolTx:
        return cls(id=data["id"], status=data["status"], transaction=data["transaction"])


@dataclass(frozen=True)
class FeeRate:
    """Atoms per kilobyte."""

    amount_per_kb: Amount

    @classmethod
    def from_json(cls, data: dict) -> FeeRate:
        return cls(amount_per_kb=Amount.from_json(data["amount_per_kb"]))


@dataclass(frozen=True)
class FeeRatePoint:
    """Wire shape: ``[size, {"amount_per_kb": {...}}]``."""

    size: int
    rate: FeeRate

    @classmethod
    def from_json(cls, data: Any) -> FeeRatePoint:
        size, rate = data
        return cls(size=size, rate=FeeRate.from_json(rate))


@dataclass(frozen=True)
class PeerInfo:
    peer_id: int
    address: str
    peer_role: str
    ban_score: int
    user_agent: str
    software_version: str
    ping_wait: int | None = None
    ping_last: int | None = None
    ping_min: int | None = None
    last_tip_block_time: int | None = None

    @classmethod
    def from_json(cls, data: dict) -> PeerInfo:
        return cls(
            peer_id=data["peer_id"],
            address=data["address"],
            peer_role=data["peer_role"],
            ban_score=data["ban_score"],
            user_agent=data["user_agent"],
            software_version=data["software_version"],
            ping_wait=data.get("ping_wait"),
            ping_last=data.get("ping_last"),
            ping_min=data.get("ping_min"),
            last_tip_block_time=data.get("last_tip_block_time"),
        )


@dataclass(frozen=True)
class BannedPeer:
    """Wire shape: ``["<ip>", {"time": [secs, nanos]}]``."""

    address: str
    ban_time: tuple[int, int]

    @classmethod
    def from_json(cls, data: Any) -> BannedPeer:
        address, payload = data
        secs, nanos = payload["time"]
        return cls(address=address, ban_time=(secs, nanos))
