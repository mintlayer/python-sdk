"""Token methods (mirrors go-sdk/wallet/tokens.go)."""

from __future__ import annotations

from ._core import _WalletCore
from .types import (
    ChangeAuthorityParams,
    FreezeParams,
    IssueNFTParams,
    IssueTokenParams,
    IssueTokenResult,
    LockSupplyParams,
    MintParams,
    SendResult,
    TokenSendParams,
    UnfreezeParams,
    UnmintParams,
)


class TokensMixin(_WalletCore):
    def issue_token(self, params: IssueTokenParams) -> IssueTokenResult:
        """Issue a new fungible token."""
        return self._call_model("token_issue_new", params.to_json(), IssueTokenResult)

    def issue_nft(self, params: IssueNFTParams) -> IssueTokenResult:
        """Issue a new NFT (returns the token ID)."""
        return self._call_model("token_nft_issue_new", params.to_json(), IssueTokenResult)

    def mint_tokens(self, params: MintParams) -> SendResult:
        """Mint additional supply of a token."""
        return self._call_model("token_mint", params.to_json(), SendResult)

    def unmint_tokens(self, params: UnmintParams) -> SendResult:
        """Burn token supply."""
        return self._call_model("token_unmint", params.to_json(), SendResult)

    def lock_token_supply(self, params: LockSupplyParams) -> SendResult:
        """Permanently lock a token's supply (wire key: ``account_index``)."""
        return self._call_model("token_lock_supply", params.to_json(), SendResult)

    def freeze_token(self, params: FreezeParams) -> SendResult:
        """Freeze a token, choosing whether it can later be unfrozen."""
        return self._call_model("token_freeze", params.to_json(), SendResult)

    def unfreeze_token(self, params: UnfreezeParams) -> SendResult:
        """Unfreeze a token."""
        return self._call_model("token_unfreeze", params.to_json(), SendResult)

    def change_token_authority(self, params: ChangeAuthorityParams) -> SendResult:
        """Transfer a token's authority to a new address."""
        return self._call_model("token_change_authority", params.to_json(), SendResult)

    def send_token(self, params: TokenSendParams) -> SendResult:
        """Send tokens (alias of :meth:`TransactionsMixin.token_send`)."""
        return self._call_model("token_send", params.to_json(), SendResult)
