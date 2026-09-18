"""Shared helpers for the WASM client tests.

All WASM tests run fully offline: the embedded ``wasm_wrappers_bg.wasm``
module is instantiated in-process via wasmtime, no node/daemon/network is
needed. Values pinned here are real test vectors taken from the Mintlayer
sources (mintlayer-core) so the WASM module accepts them.
"""

from __future__ import annotations

from mintlayer.wasm import (
    Amount,
    Client,
    Network,
    SignatureHashType,
    SourceId,
    TxAdditionalInfo,
)

# The canonical BIP-39 test mnemonic ("abandon ... about").
MNEMONIC = "abandon " * 11 + "about"

# A valid mainnet VRF public key: bech32m HRP "mvrfpk", payload
# 0x00 (Schnorrkel variant tag) + 32-byte key. Taken from the
# example_mainnet_vrf test in mintlayer-core common/src/address/hexified.rs.
VRF_MAINNET = "mvrfpk1qqyxcl4tc6y9amf2vmv6sgu8x5jwqlxawx73vhgemkduag9c8ku57m03mze"

# Height used across fee/staking/ids calls (post all early forks).
HEIGHT = 500_000
# Height at/after the orders V1 fork (encode_input_for_freeze_order).
ORDERS_HEIGHT = 1_000_000


def derive(c: Client) -> tuple[bytes, bytes, bytes, str]:
    """Derive the standard (account, receiving key, pubkey, address) chain."""
    account = c.make_default_account_privkey(MNEMONIC, Network.MAINNET)
    recv = c.make_receiving_address(account, 0)
    pub = c.public_key_from_private_key(recv)
    addr = c.pubkey_to_pubkeyhash_address(pub, Network.MAINNET)
    return account, recv, pub, addr


class Wallet:
    """Derived identity bundle for one client (fixed by the test mnemonic)."""

    def __init__(self, c: Client) -> None:
        self.account, self.recv, self.pub, self.addr = derive(c)


def fake_input(c: Client, txid: bytes = b"\x01" * 32, index: int = 0) -> bytes:
    """A real encoded UTXO input spending ``txid`` output ``index``."""
    src = c.encode_outpoint_source_id(txid, SourceId.SOURCE_TRANSACTION)
    return c.encode_input_for_utxo(src, index)


def simple_transfer_tx(c: Client, wallet: Wallet) -> tuple[bytes, bytes, bytes]:
    """Build (input, output, unsigned tx) sending 1 ML back to ``wallet``."""
    inp = fake_input(c)
    out = c.encode_output_transfer(Amount.from_atoms("100000000000"), wallet.addr, Network.MAINNET)
    tx = c.encode_transaction(inp, out, 0)
    return inp, out, tx


def witness_for(c: Client, wallet: Wallet, inp: bytes, out: bytes, tx: bytes) -> bytes:
    """Sign input 0 of ``tx`` with the wallet's receiving key."""
    return c.encode_witness(
        SignatureHashType.SIGHASH_ALL,
        wallet.recv,
        wallet.addr,
        tx,
        b"\x01" + out,
        0,
        TxAdditionalInfo(),
        100,
        Network.MAINNET,
    )


class MemorySpy:
    """Proxy for ``client.memory`` recording zero-filled writes.

    ``_core._call_return_*`` zeroes result buffers that carried key material
    before releasing them; the spy lets tests observe that contract.
    """

    def __init__(self, mem) -> None:
        self._mem = mem
        self.zero_writes: list[int] = []

    def read(self, *args):  # noqa: ANN002, ANN003 - passthrough
        return self._mem.read(*args)

    def write(self, store, data, ptr):  # noqa: ANN001 - passthrough
        if len(data) > 0 and set(data) <= {0}:
            self.zero_writes.append(len(data))
        return self._mem.write(store, data, ptr)
