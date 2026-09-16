"""Token / NFT endpoints (mirrors go-sdk/indexer/token.go)."""

from __future__ import annotations

from ._core import IndexerCore, _seg
from .types import NFTInfo, PageOpts, TokenInfo, TokenTx


class TokenMixin(IndexerCore):
    def list_tokens(self, opts: PageOpts | None = None) -> list[str]:
        """List token IDs with pagination."""
        return self._get("/token", (opts or PageOpts()).query()) or []

    def get_token(self, token_id: str) -> TokenInfo:
        """Return token info by ID."""
        return TokenInfo.from_json(self._get(f"/token/{_seg(token_id)}"))

    def get_token_transactions(self, token_id: str, opts: PageOpts | None = None) -> list[TokenTx]:
        """List transactions involving the token."""
        data = self._get(f"/token/{_seg(token_id)}/transactions", (opts or PageOpts()).query())
        return [TokenTx.from_json(t) for t in data or []]

    def find_tokens_by_ticker(self, ticker: str, opts: PageOpts | None = None) -> list[str]:
        """Find token IDs by ticker symbol."""
        return self._get(f"/token/ticker/{_seg(ticker)}", (opts or PageOpts()).query()) or []

    def get_nft(self, token_id: str) -> NFTInfo:
        """Return NFT info by token ID."""
        return NFTInfo.from_json(self._get(f"/nft/{_seg(token_id)}"))
