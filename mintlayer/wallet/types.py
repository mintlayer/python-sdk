"""Types for the wallet JSON-RPC client (mirrors go-sdk/wallet/types.go and friends).

Wire-fidelity notes (all verified against the Go structs):

* pointer fields WITHOUT ``omitempty`` serialise as JSON ``null`` when unset —
  the dominant pattern for optional strings;
* ``omitempty`` applies only to: ``Amount.atoms``/``Amount.decimal``,
  ``SendParams.selected_utxos``, ``MnemonicResult.content``,
  ``CreateWalletResult.mnemonic``, ``TokenSupply.content``, ``TxInspection.fees``;
* ``TxOptions`` always serialises both keys (null when unset);
* ``OutputValue`` and ``CurrencyFilter`` use fully custom encodings.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "Amount",
    "Timestamp",
    "TxOptions",
    "OutpointSourceID",
    "Outpoint",
    "FeesBreakdown",
    "SendResult",
    "SubmitResult",
    "ComposedTx",
    "SignedTx",
    "TxStats",
    "TxInspection",
    "WalletTx",
    "MnemonicContent",
    "MnemonicResult",
    "CreateWalletResult",
    "CreateWalletParams",
    "RecoverWalletParams",
    "WalletExtraInfo",
    "WalletInfo",
    "BestBlock",
    "AccountInfo",
    "Balance",
    "AddressWithUsage",
    "RevealPublicKeyResult",
    "SendParams",
    "SweepParams",
    "UTXOSpendParams",
    "ComposeParams",
    "StakingStatus",
    "CreatePoolParams",
    "DecommissionParams",
    "OwnedPool",
    "CreateDelegationParams",
    "CreateDelegationResult",
    "DelegateParams",
    "WithdrawParams",
    "DelegationInfo",
    "TokenSupply",
    "TokenMetadata",
    "IssueTokenParams",
    "IssueTokenResult",
    "NFTMetadata",
    "IssueNFTParams",
    "MintParams",
    "UnmintParams",
    "LockSupplyParams",
    "FreezeParams",
    "UnfreezeParams",
    "ChangeAuthorityParams",
    "TokenSendParams",
    "OutputValue",
    "CurrencyFilter",
    "OrderState",
    "OwnOrder",
    "ActiveOrder",
    "OrderCreated",
    "CreateOrderParams",
    "ConcludeOrderParams",
    "FillOrderParams",
    "FreezeOrderParams",
    "ListOrdersParams",
]


@dataclass(frozen=True)
class Amount:
    """Coin/token amount; at least one of atoms/decimal must be set when sending."""

    atoms: str = ""
    decimal: str = ""

    def to_json(self) -> dict:
        out: dict[str, str] = {}
        if self.atoms:
            out["atoms"] = self.atoms
        if self.decimal:
            out["decimal"] = self.decimal
        return out

    @classmethod
    def from_json(cls, data: dict) -> Amount:
        return cls(atoms=data.get("atoms", ""), decimal=data.get("decimal", ""))


@dataclass(frozen=True)
class Timestamp:
    timestamp: int

    @classmethod
    def from_json(cls, data: dict) -> Timestamp:
        return cls(timestamp=int(data["timestamp"]))


@dataclass(frozen=True)
class TxOptions:
    """Fee/broadcast options; both keys are always present on the wire."""

    in_top_x_mb: int | None = None
    broadcast_to_mempool: bool | None = None

    def to_json(self) -> dict:
        return {"in_top_x_mb": self.in_top_x_mb, "broadcast_to_mempool": self.broadcast_to_mempool}


@dataclass
class OutpointSourceID:
    """Tagged union: ``"Transaction"`` (content ``{"tx_id": hex}``) or
    ``"BlockReward"`` (content ``{"block_id": hex}``). Content is raw JSON and
    always serialised (null when unset), mirroring the Go struct."""

    type: str
    content: Any = None

    def to_json(self) -> dict:
        return {"type": self.type, "content": self.content}

    @classmethod
    def from_json(cls, data: dict) -> OutpointSourceID:
        return cls(type=data["type"], content=data.get("content"))


@dataclass(frozen=True)
class Outpoint:
    source_id: OutpointSourceID
    index: int

    def to_json(self) -> dict:
        return {"source_id": self.source_id.to_json(), "index": self.index}

    @classmethod
    def from_json(cls, data: dict) -> Outpoint:
        return cls(
            source_id=OutpointSourceID.from_json(data["source_id"]),
            index=data["index"],
        )


@dataclass(frozen=True)
class FeesBreakdown:
    coins: Amount
    tokens: dict[str, Amount]

    @classmethod
    def from_json(cls, data: dict) -> FeesBreakdown:
        return cls(
            coins=Amount.from_json(data.get("coins", {})),
            tokens={k: Amount.from_json(v) for k, v in (data.get("tokens") or {}).items()},
        )


@dataclass(frozen=True)
class SendResult:
    tx_id: str
    fees: FeesBreakdown
    broadcasted: bool

    @classmethod
    def from_json(cls, data: dict) -> SendResult:
        return cls(
            tx_id=data["tx_id"],
            fees=FeesBreakdown.from_json(data["fees"]),
            broadcasted=data["broadcasted"],
        )


@dataclass(frozen=True)
class SubmitResult:
    tx_id: str

    @classmethod
    def from_json(cls, data: dict) -> SubmitResult:
        return cls(tx_id=data["tx_id"])


@dataclass(frozen=True)
class ComposedTx:
    """Hex-encoded PartiallySignedTransaction plus its fee breakdown."""

    hex: str
    fees: FeesBreakdown

    @classmethod
    def from_json(cls, data: dict) -> ComposedTx:
        return cls(hex=data["hex"], fees=FeesBreakdown.from_json(data["fees"]))


@dataclass(frozen=True)
class SignedTx:
    hex: str
    current_signatures: Any

    @classmethod
    def from_json(cls, data: dict) -> SignedTx:
        return cls(hex=data["hex"], current_signatures=data.get("current_signatures"))


@dataclass(frozen=True)
class TxStats:
    num_inputs: int
    total_signatures: int

    @classmethod
    def from_json(cls, data: dict) -> TxStats:
        return cls(num_inputs=data["num_inputs"], total_signatures=data["total_signatures"])


@dataclass(frozen=True)
class TxInspection:
    stats: TxStats
    fees: FeesBreakdown | None = None

    @classmethod
    def from_json(cls, data: dict) -> TxInspection:
        return cls(
            stats=TxStats.from_json(data["stats"]),
            fees=FeesBreakdown.from_json(data["fees"]) if data.get("fees") else None,
        )


@dataclass(frozen=True)
class WalletTx:
    id: str
    height: int
    timestamp: Timestamp

    @classmethod
    def from_json(cls, data: dict) -> WalletTx:
        return cls(
            id=data["id"],
            height=data["height"],
            timestamp=Timestamp.from_json(data["timestamp"]),
        )


# ── wallet management ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MnemonicContent:
    mnemonic: str


@dataclass(frozen=True)
class MnemonicResult:
    type: str
    content: MnemonicContent | None = None

    @classmethod
    def from_json(cls, data: dict) -> MnemonicResult:
        content = data.get("content")
        return cls(
            type=data["type"],
            content=MnemonicContent(**content) if content else None,
        )


@dataclass(frozen=True)
class CreateWalletResult:
    mnemonic: MnemonicResult | None = None

    @classmethod
    def from_json(cls, data: dict) -> CreateWalletResult:
        mnemonic = data.get("mnemonic")
        return cls(mnemonic=MnemonicResult.from_json(mnemonic) if mnemonic else None)


@dataclass(frozen=True)
class CreateWalletParams:
    path: str
    store_seed_phrase: bool
    mnemonic: str | None = None
    passphrase: str | None = None
    hardware_wallet: str | None = None

    def to_json(self) -> dict:
        return {
            "path": self.path,
            "store_seed_phrase": self.store_seed_phrase,
            "mnemonic": self.mnemonic,
            "passphrase": self.passphrase,
            "hardware_wallet": self.hardware_wallet,
        }


@dataclass(frozen=True)
class RecoverWalletParams:
    path: str
    store_seed_phrase: bool
    mnemonic: str
    passphrase: str | None = None
    hardware_wallet: str | None = None

    def to_json(self) -> dict:
        return {
            "path": self.path,
            "store_seed_phrase": self.store_seed_phrase,
            "mnemonic": self.mnemonic,
            "passphrase": self.passphrase,
            "hardware_wallet": self.hardware_wallet,
        }


@dataclass(frozen=True)
class WalletExtraInfo:
    type: str

    @classmethod
    def from_json(cls, data: dict) -> WalletExtraInfo:
        return cls(type=data["type"])


@dataclass(frozen=True)
class WalletInfo:
    wallet_id: str
    account_names: list[str]
    extra_info: WalletExtraInfo

    @classmethod
    def from_json(cls, data: dict) -> WalletInfo:
        return cls(
            wallet_id=data["wallet_id"],
            account_names=data.get("account_names") or [],
            extra_info=WalletExtraInfo.from_json(data["extra_info"]),
        )


@dataclass(frozen=True)
class BestBlock:
    height: int
    id: str

    @classmethod
    def from_json(cls, data: dict) -> BestBlock:
        return cls(height=data["height"], id=data["id"])


@dataclass(frozen=True)
class AccountInfo:
    account: int
    name: str

    @classmethod
    def from_json(cls, data: dict) -> AccountInfo:
        return cls(account=data["account"], name=data["name"])


@dataclass(frozen=True)
class Balance:
    coins: Amount
    tokens: dict[str, Amount]

    @classmethod
    def from_json(cls, data: dict) -> Balance:
        return cls(
            coins=Amount.from_json(data.get("coins", {})),
            tokens={k: Amount.from_json(v) for k, v in (data.get("tokens") or {}).items()},
        )


@dataclass(frozen=True)
class AddressWithUsage:
    address: str
    used: bool
    coins: Amount

    @classmethod
    def from_json(cls, data: dict) -> AddressWithUsage:
        return cls(
            address=data["address"],
            used=data["used"],
            coins=Amount.from_json(data["coins"]),
        )


@dataclass(frozen=True)
class RevealPublicKeyResult:
    public_key_hex: str
    public_key_address: str

    @classmethod
    def from_json(cls, data: dict) -> RevealPublicKeyResult:
        return cls(
            public_key_hex=data["public_key_hex"], public_key_address=data["public_key_address"]
        )


# ── transactions ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SendParams:
    account: int
    address: str
    amount: Amount
    selected_utxos: list[Outpoint] | None = None
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        out: dict[str, Any] = {
            "account": self.account,
            "address": self.address,
            "amount": self.amount.to_json(),
            "options": self.options.to_json(),
        }
        # omitempty: nil OR empty selected_utxos is omitted from the wire.
        if self.selected_utxos:
            out["selected_utxos"] = [u.to_json() for u in self.selected_utxos]
        return out


@dataclass(frozen=True)
class SweepParams:
    account: int
    destination_address: str
    from_addresses: list[str] = field(default_factory=list)
    all: bool = False
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "destination_address": self.destination_address,
            "from_addresses": self.from_addresses,
            "all": self.all,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class UTXOSpendParams:
    account: int
    utxo: Outpoint
    output_address: str
    htlc_secret: str | None = None
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "utxo": self.utxo.to_json(),
            "output_address": self.output_address,
            "htlc_secret": self.htlc_secret,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class ComposeParams:
    inputs: list[Outpoint] = field(default_factory=list)
    outputs: list[Any] = field(default_factory=list)
    htlc_secrets: Any = None
    only_transaction: bool = False

    def to_json(self) -> dict:
        return {
            "inputs": [i.to_json() for i in self.inputs],
            "outputs": self.outputs,
            "htlc_secrets": self.htlc_secrets,
            "only_transaction": self.only_transaction,
        }


# ── staking ──────────────────────────────────────────────────────────────────


class StakingStatus(str, enum.Enum):
    ACTIVE = "Staking"
    INACTIVE = "NotStaking"


@dataclass(frozen=True)
class CreatePoolParams:
    account: int
    amount: Amount
    cost_per_block: Amount
    margin_ratio_per_thousand: str
    decommission_address: str
    staker_address: str | None = None
    vrf_public_key: str | None = None
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "amount": self.amount.to_json(),
            "cost_per_block": self.cost_per_block.to_json(),
            "margin_ratio_per_thousand": self.margin_ratio_per_thousand,
            "decommission_address": self.decommission_address,
            "staker_address": self.staker_address,
            "vrf_public_key": self.vrf_public_key,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class DecommissionParams:
    account: int
    pool_id: str
    output_address: str
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "pool_id": self.pool_id,
            "output_address": self.output_address,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class OwnedPool:
    pool_id: str
    pledge: Amount
    balance: Amount
    margin_ratio_per_thousand: str
    cost_per_block: Amount

    @classmethod
    def from_json(cls, data: dict) -> OwnedPool:
        return cls(
            pool_id=data["pool_id"],
            pledge=Amount.from_json(data["pledge"]),
            balance=Amount.from_json(data["balance"]),
            margin_ratio_per_thousand=data["margin_ratio_per_thousand"],
            cost_per_block=Amount.from_json(data["cost_per_block"]),
        )


@dataclass(frozen=True)
class CreateDelegationParams:
    account: int
    address: str
    pool_id: str
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "address": self.address,
            "pool_id": self.pool_id,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class CreateDelegationResult:
    delegation_id: str
    tx_id: str

    @classmethod
    def from_json(cls, data: dict) -> CreateDelegationResult:
        return cls(delegation_id=data["delegation_id"], tx_id=data["tx_id"])


@dataclass(frozen=True)
class DelegateParams:
    account: int
    amount: Amount
    delegation_id: str
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "amount": self.amount.to_json(),
            "delegation_id": self.delegation_id,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class WithdrawParams:
    account: int
    address: str
    amount: Amount
    delegation_id: str
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "address": self.address,
            "amount": self.amount.to_json(),
            "delegation_id": self.delegation_id,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class DelegationInfo:
    delegation_id: str
    pool_id: str
    balance: Amount

    @classmethod
    def from_json(cls, data: dict) -> DelegationInfo:
        return cls(
            delegation_id=data["delegation_id"],
            pool_id=data["pool_id"],
            balance=Amount.from_json(data["balance"]),
        )


# ── tokens ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TokenSupply:
    """``"Fixed"`` | ``"Lockable"`` | ``"Unlimited"``; content only for Fixed."""

    type: str
    content: Amount | None = None

    def to_json(self) -> dict:
        out: dict[str, Any] = {"type": self.type}
        if self.content is not None:
            out["content"] = self.content.to_json()
        return out


@dataclass(frozen=True)
class TokenMetadata:
    token_ticker: str
    number_of_decimals: int
    metadata_uri: str
    token_supply: TokenSupply
    is_freezable: bool

    def to_json(self) -> dict:
        return {
            "token_ticker": self.token_ticker,
            "number_of_decimals": self.number_of_decimals,
            "metadata_uri": self.metadata_uri,
            "token_supply": self.token_supply.to_json(),
            "is_freezable": self.is_freezable,
        }


@dataclass(frozen=True)
class IssueTokenParams:
    account: int
    destination_address: str
    metadata: TokenMetadata
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "destination_address": self.destination_address,
            "metadata": self.metadata.to_json(),
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class IssueTokenResult:
    token_id: str
    tx_id: str

    @classmethod
    def from_json(cls, data: dict) -> IssueTokenResult:
        return cls(token_id=data["token_id"], tx_id=data["tx_id"])


@dataclass(frozen=True)
class NFTMetadata:
    media_hash: str
    name: str
    description: str
    ticker: str
    creator: str | None = None
    icon_uri: str | None = None
    media_uri: str | None = None
    additional_metadata_uri: str | None = None

    def to_json(self) -> dict:
        return {
            "media_hash": self.media_hash,
            "name": self.name,
            "description": self.description,
            "ticker": self.ticker,
            "creator": self.creator,
            "icon_uri": self.icon_uri,
            "media_uri": self.media_uri,
            "additional_metadata_uri": self.additional_metadata_uri,
        }


@dataclass(frozen=True)
class IssueNFTParams:
    account: int
    destination_address: str
    metadata: NFTMetadata
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "destination_address": self.destination_address,
            "metadata": self.metadata.to_json(),
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class MintParams:
    account: int
    token_id: str
    address: str
    amount: Amount
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "token_id": self.token_id,
            "address": self.address,
            "amount": self.amount.to_json(),
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class UnmintParams:
    account: int
    token_id: str
    amount: Amount
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "token_id": self.token_id,
            "amount": self.amount.to_json(),
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class LockSupplyParams:
    """Wire key note: the account field is sent as ``account_index``."""

    account_index: int
    token_id: str
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account_index": self.account_index,
            "token_id": self.token_id,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class FreezeParams:
    account: int
    token_id: str
    is_unfreezable: bool
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "token_id": self.token_id,
            "is_unfreezable": self.is_unfreezable,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class UnfreezeParams:
    account: int
    token_id: str
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "token_id": self.token_id,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class ChangeAuthorityParams:
    account: int
    token_id: str
    address: str
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "token_id": self.token_id,
            "address": self.address,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class TokenSendParams:
    account: int
    token_id: str
    address: str
    amount: Amount
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "token_id": self.token_id,
            "address": self.address,
            "amount": self.amount.to_json(),
            "options": self.options.to_json(),
        }


# ── DEX orders ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OutputValue:
    """Custom wire encoding for one side of an order.

    * Coin:  ``{"type":"Coin","content":{"amount":{"atoms":...,"decimal":...}}}``
    * Token: ``{"type":"Token","content":{"id":"<bech32>","amount":{...}}}``

    Validation errors (missing amount / missing token id) are raised before
    any HTTP request is sent.
    """

    coin: bool
    token_id: str
    amount: Amount

    @classmethod
    def coins(cls, atoms: str, decimal: str = "") -> OutputValue:
        return cls(coin=True, token_id="", amount=Amount(atoms=atoms, decimal=decimal))

    @classmethod
    def tokens(cls, token_id: str, atoms: str, decimal: str = "") -> OutputValue:
        return cls(coin=False, token_id=token_id, amount=Amount(atoms=atoms, decimal=decimal))

    def to_json(self) -> dict:
        if not self.amount.atoms and not self.amount.decimal:
            raise ValueError("wallet: output value requires an amount")
        if self.coin:
            return {"type": "Coin", "content": {"amount": self.amount.to_json()}}
        if not self.token_id:
            raise ValueError("wallet: token OutputValue requires TokenID")
        return {
            "type": "Token",
            "content": {"id": self.token_id, "amount": self.amount.to_json()},
        }

    @classmethod
    def from_json(cls, data: dict) -> OutputValue:
        kind = data.get("type")
        if not kind:
            raise ValueError("wallet: output value requires a type")
        content = data.get("content") or {}
        amount = Amount.from_json(content.get("amount") or {})
        if not amount.atoms and not amount.decimal:
            raise ValueError("wallet: output value requires an amount")
        if kind == "Coin":
            return cls(coin=True, token_id="", amount=amount)
        if kind == "Token":
            token_id = content.get("id", "")
            if not token_id:
                raise ValueError("wallet: token OutputValue requires TokenID")
            return cls(coin=False, token_id=token_id, amount=amount)
        raise ValueError(f"wallet: unknown OutputValue type {kind!r}")


@dataclass(frozen=True)
class CurrencyFilter:
    """Custom wire encoding: ``CoinFilter()`` → ``{"type":"Coin"}`` (no content
    key); ``TokenFilter(id)`` → ``{"type":"Token","content":"<id>"}``."""

    coin: bool
    content: str = ""

    @classmethod
    def coin_filter(cls) -> CurrencyFilter:
        return cls(coin=True)

    @classmethod
    def token_filter(cls, token_id: str) -> CurrencyFilter:
        if not token_id:
            raise ValueError(
                "wallet: TokenFilter requires a token id (use CoinFilter for the native coin)"
            )
        return cls(coin=False, content=token_id)

    def to_json(self) -> dict:
        if self.coin:
            return {"type": "Coin"}
        return {"type": "Token", "content": self.content}


@dataclass(frozen=True)
class OrderState:
    ask_balance: Amount
    give_balance: Amount
    is_frozen: bool
    creation_timestamp: Timestamp

    @classmethod
    def from_json(cls, data: dict) -> OrderState:
        return cls(
            ask_balance=Amount.from_json(data["ask_balance"]),
            give_balance=Amount.from_json(data["give_balance"]),
            is_frozen=data["is_frozen"],
            creation_timestamp=Timestamp.from_json(data["creation_timestamp"]),
        )


@dataclass(frozen=True)
class OwnOrder:
    order_id: str
    initially_asked: OutputValue
    initially_given: OutputValue
    existing_order_data: OrderState | None
    is_marked_as_frozen_in_wallet: bool
    is_marked_as_concluded_in_wallet: bool

    @classmethod
    def from_json(cls, data: dict) -> OwnOrder:
        existing = data.get("existing_order_data")
        return cls(
            order_id=data["order_id"],
            initially_asked=OutputValue.from_json(data["initially_asked"]),
            initially_given=OutputValue.from_json(data["initially_given"]),
            existing_order_data=OrderState.from_json(existing) if existing else None,
            is_marked_as_frozen_in_wallet=data["is_marked_as_frozen_in_wallet"],
            is_marked_as_concluded_in_wallet=data["is_marked_as_concluded_in_wallet"],
        )


@dataclass(frozen=True)
class ActiveOrder:
    order_id: str
    initially_asked: OutputValue
    initially_given: OutputValue
    ask_balance: Amount
    give_balance: Amount
    is_own: bool

    @classmethod
    def from_json(cls, data: dict) -> ActiveOrder:
        return cls(
            order_id=data["order_id"],
            initially_asked=OutputValue.from_json(data["initially_asked"]),
            initially_given=OutputValue.from_json(data["initially_given"]),
            ask_balance=Amount.from_json(data["ask_balance"]),
            give_balance=Amount.from_json(data["give_balance"]),
            is_own=data["is_own"],
        )


@dataclass(frozen=True)
class OrderCreated:
    order_id: str
    tx_id: str
    broadcasted: bool

    @classmethod
    def from_json(cls, data: dict) -> OrderCreated:
        return cls(
            order_id=data["order_id"],
            tx_id=data["tx_id"],
            broadcasted=data["broadcasted"],
        )


@dataclass(frozen=True)
class CreateOrderParams:
    account: int
    ask: OutputValue
    give: OutputValue
    conclude_address: str
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "ask": self.ask.to_json(),
            "give": self.give.to_json(),
            "conclude_address": self.conclude_address,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class ConcludeOrderParams:
    account: int
    order_id: str
    output_address: str | None = None
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "order_id": self.order_id,
            "output_address": self.output_address,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class FillOrderParams:
    account: int
    order_id: str
    fill_amount_in_ask_currency: Amount
    output_address: str | None = None
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "order_id": self.order_id,
            "fill_amount_in_ask_currency": self.fill_amount_in_ask_currency.to_json(),
            "output_address": self.output_address,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class FreezeOrderParams:
    account: int
    order_id: str
    options: TxOptions = field(default_factory=TxOptions)

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "order_id": self.order_id,
            "options": self.options.to_json(),
        }


@dataclass(frozen=True)
class ListOrdersParams:
    account: int
    ask_currency: CurrencyFilter | None = None
    give_currency: CurrencyFilter | None = None

    def to_json(self) -> dict:
        return {
            "account": self.account,
            "ask_currency": self.ask_currency.to_json() if self.ask_currency else None,
            "give_currency": self.give_currency.to_json() if self.give_currency else None,
        }
