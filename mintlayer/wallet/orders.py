"""DEX order methods (mirrors go-sdk/wallet/orders.go)."""

from __future__ import annotations

from ._core import _WalletCore
from .types import (
    ActiveOrder,
    ConcludeOrderParams,
    CreateOrderParams,
    CurrencyFilter,
    FillOrderParams,
    FreezeOrderParams,
    ListOrdersParams,
    OrderCreated,
    OwnOrder,
    SendResult,
)


class OrdersMixin(_WalletCore):
    def create_order(self, params: CreateOrderParams) -> OrderCreated:
        """Create a new DEX order."""
        return self._call_model("order_create", params.to_json(), OrderCreated)

    def conclude_order(self, params: ConcludeOrderParams) -> SendResult:
        """Conclude an order owned by the account."""
        return self._call_model("order_conclude", params.to_json(), SendResult)

    def fill_order(self, params: FillOrderParams) -> SendResult:
        """Fill (partially or fully) an existing order."""
        return self._call_model("order_fill", params.to_json(), SendResult)

    def freeze_order(self, params: FreezeOrderParams) -> SendResult:
        """Freeze an order (orders V1 fork only)."""
        return self._call_model("order_freeze", params.to_json(), SendResult)

    def list_own_orders(self, account: int) -> list[OwnOrder]:
        """List the account's own orders."""
        return self._call_model_list("order_list_own", {"account": account}, OwnOrder)

    def list_all_active_orders(self, params: ListOrdersParams) -> list[ActiveOrder]:
        """List all active orders, optionally filtered by currency pair
        (``None`` filters match any)."""
        return self._call_model_list("order_list_all_active", params.to_json(), ActiveOrder)


def coin_filter() -> CurrencyFilter:
    """Currency filter matching the native coin (wire: ``{"type":"Coin"}``)."""
    return CurrencyFilter.coin_filter()


def token_filter(token_id: str) -> CurrencyFilter:
    """Currency filter matching a token (wire: ``{"type":"Token","content":id}``)."""
    return CurrencyFilter.token_filter(token_id)
