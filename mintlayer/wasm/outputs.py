"""Transaction output encoding (mirrors go-sdk/wasm/outputs.go)."""

from __future__ import annotations

from ._core import _WasmCore
from ._util import synchronized
from .types import Amount, FreezableToken, Network, TotalSupply


class OutputsMixin(_WasmCore):
    @synchronized
    def encode_output_transfer(self, amount: Amount, address: str, network: Network) -> bytes:
        """Create a Transfer output sending coins to an address."""
        amt_ptr = self._new_wasm_amount(amount)
        addr_ptr, addr_len = self._write_string(address)
        return self._call_return_bytes(
            "encode_output_transfer", amt_ptr, addr_ptr, addr_len, int(network)
        )

    @synchronized
    def encode_output_token_transfer(
        self, amount: Amount, address: str, token_id: str, network: Network
    ) -> bytes:
        """Create a Transfer output sending tokens to an address."""
        amt_ptr = self._new_wasm_amount(amount)
        addr_ptr, addr_len = self._write_string(address)
        tid_ptr, tid_len = self._write_string(token_id)
        return self._call_return_bytes(
            "encode_output_token_transfer",
            amt_ptr,
            addr_ptr,
            addr_len,
            tid_ptr,
            tid_len,
            int(network),
        )

    @synchronized
    def encode_output_lock_then_transfer(
        self, amount: Amount, address: str, lock: bytes, network: Network
    ) -> bytes:
        """Create a LockThenTransfer output for coins.

        ``lock`` is an encoded timelock (see ``encode_lock_for_*``).
        """
        amt_ptr = self._new_wasm_amount(amount)
        addr_ptr, addr_len = self._write_string(address)
        lock_ptr, lock_len = self._write_bytes(lock)
        return self._call_return_bytes(
            "encode_output_lock_then_transfer",
            amt_ptr,
            addr_ptr,
            addr_len,
            lock_ptr,
            lock_len,
            int(network),
        )

    @synchronized
    def encode_output_token_lock_then_transfer(
        self, amount: Amount, address: str, token_id: str, lock: bytes, network: Network
    ) -> bytes:
        """Create a LockThenTransfer output for tokens."""
        amt_ptr = self._new_wasm_amount(amount)
        addr_ptr, addr_len = self._write_string(address)
        tid_ptr, tid_len = self._write_string(token_id)
        lock_ptr, lock_len = self._write_bytes(lock)
        return self._call_return_bytes(
            "encode_output_token_lock_then_transfer",
            amt_ptr,
            addr_ptr,
            addr_len,
            tid_ptr,
            tid_len,
            lock_ptr,
            lock_len,
            int(network),
        )

    @synchronized
    def encode_output_coin_burn(self, amount: Amount) -> bytes:
        """Create a Burn output for coins."""
        amt_ptr = self._new_wasm_amount(amount)
        return self._call_return_bytes("encode_output_coin_burn", amt_ptr)

    @synchronized
    def encode_output_token_burn(self, amount: Amount, token_id: str, network: Network) -> bytes:
        """Create a Burn output for tokens."""
        amt_ptr = self._new_wasm_amount(amount)
        tid_ptr, tid_len = self._write_string(token_id)
        return self._call_return_bytes(
            "encode_output_token_burn", amt_ptr, tid_ptr, tid_len, int(network)
        )

    @synchronized
    def encode_output_create_delegation(
        self, pool_id: str, owner_address: str, network: Network
    ) -> bytes:
        """Create an output that creates a staking delegation."""
        pid_ptr, pid_len = self._write_string(pool_id)
        addr_ptr, addr_len = self._write_string(owner_address)
        return self._call_return_bytes(
            "encode_output_create_delegation", pid_ptr, pid_len, addr_ptr, addr_len, int(network)
        )

    @synchronized
    def encode_output_delegate_staking(
        self, amount: Amount, delegation_id: str, network: Network
    ) -> bytes:
        """Create an output that delegates coins to a staking pool."""
        amt_ptr = self._new_wasm_amount(amount)
        did_ptr, did_len = self._write_string(delegation_id)
        return self._call_return_bytes(
            "encode_output_delegate_staking", amt_ptr, did_ptr, did_len, int(network)
        )

    @synchronized
    def encode_output_create_stake_pool(
        self, pool_id: str, pool_data: bytes, network: Network
    ) -> bytes:
        """Create an output that creates a staking pool.

        ``pool_data`` is encoded stake pool data (see ``encode_stake_pool_data``).
        """
        pid_ptr, pid_len = self._write_string(pool_id)
        pd_ptr, pd_len = self._write_bytes(pool_data)
        return self._call_return_bytes(
            "encode_output_create_stake_pool", pid_ptr, pid_len, pd_ptr, pd_len, int(network)
        )

    @synchronized
    def encode_output_produce_block_from_stake(
        self, pool_id: str, staker: str, network: Network
    ) -> bytes:
        """Create a ProduceBlockFromStake output.

        This UTXO is consumed when decommissioning a pool (if the pool has
        staked at least once).
        """
        pid_ptr, pid_len = self._write_string(pool_id)
        stk_ptr, stk_len = self._write_string(staker)
        return self._call_return_bytes(
            "encode_output_produce_block_from_stake",
            pid_ptr,
            pid_len,
            stk_ptr,
            stk_len,
            int(network),
        )

    @synchronized
    def encode_output_data_deposit(self, data: bytes) -> bytes:
        """Create a DataDeposit output for arbitrary on-chain data."""
        ptr, length = self._write_bytes(data)
        return self._call_return_bytes("encode_output_data_deposit", ptr, length)

    @synchronized
    def encode_output_htlc(
        self,
        amount: Amount,
        token_id: str | None,
        secret_hash: str,
        spend_address: str,
        refund_address: str,
        refund_timelock: bytes,
        network: Network,
    ) -> bytes:
        """Create a hash time-lock contract (HTLC) output for coins or tokens.

        ``token_id`` may be ``None`` for coin HTLCs. ``refund_timelock`` is an
        encoded timelock.
        """
        amt_ptr = self._new_wasm_amount(amount)
        tid_ptr, tid_len = self._write_optional_string(token_id)
        sh_ptr, sh_len = self._write_string(secret_hash)
        sa_ptr, sa_len = self._write_string(spend_address)
        ra_ptr, ra_len = self._write_string(refund_address)
        tl_ptr, tl_len = self._write_bytes(refund_timelock)
        return self._call_return_bytes(
            "encode_output_htlc",
            amt_ptr,
            tid_ptr,
            tid_len,
            sh_ptr,
            sh_len,
            sa_ptr,
            sa_len,
            ra_ptr,
            ra_len,
            tl_ptr,
            tl_len,
            int(network),
        )

    @synchronized
    def encode_output_issue_fungible_token(
        self,
        authority: str,
        token_ticker: str,
        metadata_uri: str,
        number_of_decimals: int,
        total_supply: TotalSupply,
        supply_amount: Amount | None,
        is_token_freezable: FreezableToken,
        current_block_height: int,
        network: Network,
    ) -> bytes:
        """Create an output that issues a new fungible token.

        ``supply_amount`` may be ``None`` unless ``total_supply`` is
        ``TotalSupply.FIXED``.
        """
        auth_ptr, auth_len = self._write_string(authority)
        tkr_ptr, tkr_len = self._write_string(token_ticker)
        uri_ptr, uri_len = self._write_string(metadata_uri)
        sa_ptr = 0
        if supply_amount is not None:
            sa_ptr = self._new_wasm_amount(supply_amount)
        return self._call_return_bytes(
            "encode_output_issue_fungible_token",
            auth_ptr,
            auth_len,
            tkr_ptr,
            tkr_len,
            uri_ptr,
            uri_len,
            number_of_decimals,
            int(total_supply),
            sa_ptr,
            int(is_token_freezable),
            current_block_height,
            int(network),
        )

    @synchronized
    def encode_output_issue_nft(
        self,
        token_id: str,
        authority: str,
        name: str,
        ticker: str,
        description: str,
        media_hash: bytes,
        creator: bytes | None,
        media_uri: str | None,
        icon_uri: str | None,
        additional_metadata_uri: str | None,
        current_block_height: int,
        network: Network,
    ) -> bytes:
        """Create an output that issues a new NFT.

        ``creator``, ``media_uri``, ``icon_uri`` and ``additional_metadata_uri``
        may be ``None``.
        """
        tid_ptr, tid_len = self._write_string(token_id)
        auth_ptr, auth_len = self._write_string(authority)
        name_ptr, name_len = self._write_string(name)
        tkr_ptr, tkr_len = self._write_string(ticker)
        desc_ptr, desc_len = self._write_string(description)
        mh_ptr, mh_len = self._write_bytes(media_hash)
        cr_ptr, cr_len = self._write_optional_bytes(creator)
        mu_ptr, mu_len = self._write_optional_string(media_uri)
        iu_ptr, iu_len = self._write_optional_string(icon_uri)
        am_ptr, am_len = self._write_optional_string(additional_metadata_uri)
        return self._call_return_bytes(
            "encode_output_issue_nft",
            tid_ptr,
            tid_len,
            auth_ptr,
            auth_len,
            name_ptr,
            name_len,
            tkr_ptr,
            tkr_len,
            desc_ptr,
            desc_len,
            mh_ptr,
            mh_len,
            cr_ptr,
            cr_len,
            mu_ptr,
            mu_len,
            iu_ptr,
            iu_len,
            am_ptr,
            am_len,
            current_block_height,
            int(network),
        )

    @synchronized
    def encode_create_order_output(
        self,
        ask_amount: Amount,
        ask_token_id: str | None,
        give_amount: Amount,
        give_token_id: str | None,
        conclude_address: str,
        network: Network,
    ) -> bytes:
        """Create an output that creates an order for token exchange.

        ``ask_token_id`` and ``give_token_id`` may be ``None`` for coin amounts.
        """
        ask_amt_ptr = self._new_wasm_amount(ask_amount)
        ask_tid_ptr, ask_tid_len = self._write_optional_string(ask_token_id)
        give_amt_ptr = self._new_wasm_amount(give_amount)
        give_tid_ptr, give_tid_len = self._write_optional_string(give_token_id)
        ca_ptr, ca_len = self._write_string(conclude_address)
        return self._call_return_bytes(
            "encode_create_order_output",
            ask_amt_ptr,
            ask_tid_ptr,
            ask_tid_len,
            give_amt_ptr,
            give_tid_ptr,
            give_tid_len,
            ca_ptr,
            ca_len,
            int(network),
        )
