"""Order endpoints (mirrors go-sdk/indexer/order.go)."""

from __future__ import annotations

from ._http import IndexerHTTP, _seg
from .types import Order, PageOpts


class OrderMixin(IndexerHTTP):
    def list_orders(self, opts: PageOpts | None = None) -> list[Order]:
        """List DEX orders with pagination."""
        data = self.get("/order", (opts or PageOpts()).query())
        return [Order.from_json(o) for o in data or []]

    def get_order(self, order_id: str) -> Order:
        """Return a DEX order by ID."""
        return Order.from_json(self.get(f"/order/{_seg(order_id)}"))

    def list_orders_by_pair(
        self, ask_currency: str, give_currency: str, opts: PageOpts | None = None
    ) -> list[Order]:
        """List orders for a currency pair.

        Currencies are the coin ticker (e.g. ``"ML"``) or a bech32 token ID;
        the path is ``/order/pair/{ask}_{give}``.
        """
        data = self.get(
            f"/order/pair/{_seg(ask_currency)}_{_seg(give_currency)}", (opts or PageOpts()).query()
        )
        return [Order.from_json(o) for o in data or []]
