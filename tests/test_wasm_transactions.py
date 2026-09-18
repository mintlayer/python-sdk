"""Tests for WASM transaction encoding, ids, sizes and decoding.

Mirrors go-sdk TestEncodeTransaction plus the Python-specific flows
validated against the embedded module: estimate size stability (externref
table must not leak across repeated calls), signed/partially-signed
encoding and the decode-to-JSON paths.
"""

from __future__ import annotations

import pytest
from wasm_helpers import Wallet, fake_input, witness_for
from wasmtime import Val

from mintlayer.wasm import (
    Amount,
    Client,
    Network,
    SignatureHashType,
    SourceId,
    TxAdditionalInfo,
    WasmError,
)


@pytest.fixture
def wallet(wasm: Client) -> Wallet:
    return Wallet(wasm)


@pytest.fixture
def unsigned_tx(wasm: Client, wallet: Wallet) -> tuple[bytes, bytes, bytes]:
    """(input, output, unsigned transaction) for a 1-ML self transfer."""
    inp = fake_input(wasm)
    out = wasm.encode_output_transfer(
        Amount.from_atoms("100000000000"), wallet.addr, Network.MAINNET
    )
    tx = wasm.encode_transaction(inp, out, 0)
    return inp, out, tx


def test_encode_outpoint_source_id_transaction(wasm: Client) -> None:
    src = wasm.encode_outpoint_source_id(b"\x01" * 32, SourceId.SOURCE_TRANSACTION)
    assert isinstance(src, bytes) and len(src) > 0
    assert src == wasm.encode_outpoint_source_id(b"\x01" * 32, SourceId.SOURCE_TRANSACTION)


def test_encode_outpoint_source_id_block_reward(wasm: Client) -> None:
    from_tx = wasm.encode_outpoint_source_id(b"\x01" * 32, SourceId.SOURCE_TRANSACTION)
    from_block = wasm.encode_outpoint_source_id(b"\x01" * 32, SourceId.SOURCE_BLOCK_REWARD)
    assert len(from_block) > 0
    assert from_tx != from_block, "source kind must change the encoding"


def test_encode_outpoint_source_id_wrong_length_raises(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.encode_outpoint_source_id(b"\x00" * 31, SourceId.SOURCE_TRANSACTION)


def test_encode_transaction_and_get_id(wasm: Client, unsigned_tx) -> None:
    _inp, _out, tx = unsigned_tx
    assert len(tx) > 0
    tx_id = wasm.get_transaction_id(tx, True)
    assert len(tx_id) == 64
    assert all(ch in "0123456789abcdef" for ch in tx_id)
    assert tx_id == wasm.get_transaction_id(tx, True)  # deterministic


def test_get_transaction_id_garbage_raises(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.get_transaction_id(b"garbage!", True)
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.get_transaction_id(b"\x00", False)


def test_encode_transaction_flags_change_the_id(wasm: Client, wallet: Wallet) -> None:
    inp = fake_input(wasm)
    out = wasm.encode_output_transfer(
        Amount.from_atoms("100000000000"), wallet.addr, Network.MAINNET
    )
    assert wasm.encode_transaction(inp, out, 0) != wasm.encode_transaction(inp, out, 1)


def test_estimate_transaction_size_stable(wasm: Client, wallet: Wallet, unsigned_tx) -> None:
    _inp, out, tx = unsigned_tx
    size = wasm.estimate_transaction_size(tx, [wallet.addr], out, Network.MAINNET)
    assert 0 < size < 10000
    # Repeated calls must be stable: externref table slots must not leak.
    for _ in range(100):
        repeat = wasm.estimate_transaction_size(tx, [wallet.addr], out, Network.MAINNET)
    assert repeat == size


def test_estimate_transaction_size_multiple_destinations(wallet: Wallet) -> None:
    """One destination per input; a 2-input tx estimates with 2 destinations.

    Uses a fresh client: the first multi-element string-array call on a
    client always works (later ones can hit the slot-reuse bug documented
    in test_estimate_transaction_size_multi_dest_after_repeats).
    """
    c = Client()
    try:
        inp0 = fake_input(c, txid=b"\x01" * 32)
        inp1 = fake_input(c, txid=b"\x02" * 32)
        out = c.encode_output_transfer(
            Amount.from_atoms("100000000000"), wallet.addr, Network.MAINNET
        )
        tx = c.encode_transaction(inp0 + inp1, out, 0)
        size = c.estimate_transaction_size(tx, [wallet.addr, wallet.addr], out, Network.MAINNET)
        assert size > 0
    finally:
        c.close()


def test_estimate_transaction_size_multi_dest_after_repeats(wallet: Wallet) -> None:
    """Regression: multi-destination estimates must survive interleaved use.

    Used to fail with 'array contains a value of the wrong type' after
    repeated single-destination calls: the host deallocated the callee-owned
    externref table slots after every call, double-freeing free-list entries.
    """
    c = Client()
    try:
        inp = fake_input(c)
        out = c.encode_output_transfer(
            Amount.from_atoms("100000000000"), wallet.addr, Network.MAINNET
        )
        tx = c.encode_transaction(inp, out, 0)
        assert c.estimate_transaction_size(tx, [wallet.addr], out, Network.MAINNET) > 0
        assert c.estimate_transaction_size(tx, [wallet.addr, wallet.addr], out, Network.MAINNET) > 0
        assert c.estimate_transaction_size(tx, [wallet.addr], out, Network.MAINNET) > 0
        assert c.estimate_transaction_size(tx, [wallet.addr, wallet.addr], out, Network.MAINNET) > 0
    finally:
        c.close()


def test_estimate_size_mixed_load_externref_table_stable() -> None:
    """Stress regression: mixed single/multi-destination load on one client.

    Alternates 1-3 destination ``estimate_transaction_size`` calls with
    occasional intent encode/verify rounds (multi-element externref arrays
    of both the string and Uint8Array kinds). Every call must succeed, sizes
    must stay consistent per destination count, and the wasm externref table
    must not grow across the run — table growth would mean table slots are
    leaking (the pre-fix double-dealloc corrupted the free list instead of
    recycling it).
    """
    c = Client()
    try:
        wallet = Wallet(c)
        dests = [wallet.addr] * 3
        inputs = b"".join(fake_input(c, txid=bytes([i]) * 32, index=i) for i in range(3))
        out = c.encode_output_transfer(
            Amount.from_atoms("100000000000"), wallet.addr, Network.MAINNET
        )
        tx = c.encode_transaction(inputs, out, 0)
        tx_id = c.get_transaction_id(tx, True)
        message = c.make_transaction_intent_message_to_sign("stress-intent", tx_id)

        def intent_round() -> None:
            signatures = [c.sign_challenge(wallet.recv, message) for _ in range(2)]
            encoded = c.encode_signed_transaction_intent(message, signatures)
            assert len(encoded) > 0
            c.verify_transaction_intent(message, encoded, dests[:2], Network.MAINNET)

        # Warmup with every call shape once: initial table growth (the module
        # grows its 128-slot table on first demand) must not count as a leak.
        expected: dict[int, int] = {}
        for n in (1, 2, 3):
            expected[n] = c.estimate_transaction_size(tx, dests[:n], out, Network.MAINNET)
            assert expected[n] > 0
        intent_round()
        baseline_table = c.table.size(c.store)

        for i in range(120):
            n = 1 + (i % 3)
            size = c.estimate_transaction_size(tx, dests[:n], out, Network.MAINNET)
            assert size == expected[n], f"iteration {i}: size for {n} destinations changed"
            if i % 10 == 0:
                intent_round()

        assert c.table.size(c.store) == baseline_table, (
            "externref table grew across the mixed-load run (table slot leak)"
        )
    finally:
        c.close()


def _is_null_anyref(value: object) -> bool:
    """True when wasmtime reports a null (undefined) externref table slot.

    Depending on version and context wasmtime surfaces null anyrefs either
    as ``None`` or as a ``Val`` wrapping ``None``; both mean "the slot was
    released".
    """
    if value is None:
        return True
    if isinstance(value, Val):
        return value.__dict__.get("_val", object()) is None
    return False


def _alloc_reusable_slot(c: Client) -> int:
    """Allocate one externref-table slot from the reusable region.

    The module reserves its lowest table indices as a permanent slab whose
    ``__externref_table_dealloc`` deliberately does not recycle (bounded,
    one-time JS globals); the managed region begins where a freed slot is
    handed out again via the LIFO free list. Bounded loop: the slab is finite.
    """
    for _ in range(512):
        probe = c._invoke1("__externref_table_alloc")
        c._dealloc_indices([probe])
        if c._invoke1("__externref_table_alloc") == probe:
            return probe
    raise AssertionError("no reusable externref table slot found")


def test_dealloc_indices_rollback_releases_slots_for_reuse() -> None:
    """Unit test for the pre-call rollback path: ``_dealloc_indices``.

    A rolled-back array write (failure before the WASM callee ever runs)
    must fully release the allocated externref table slots: they read back
    as null/undefined and the allocator hands them out again. This is the
    inverse contract of the post-call ownership rule (callee owns slots);
    getting either side wrong corrupts the table free list.
    """
    c = Client()
    try:
        slot_a = _alloc_reusable_slot(c)
        slot_b = _alloc_reusable_slot(c)
        assert slot_a != slot_b
        c.table.set(c.store, slot_a, "rollback-a")
        c.table.set(c.store, slot_b, "rollback-b")
        assert c.table.get(c.store, slot_a) == "rollback-a"
        assert c.table.get(c.store, slot_b) == "rollback-b"

        c._dealloc_indices([slot_a, slot_b])

        assert _is_null_anyref(c.table.get(c.store, slot_a)), "slot_a still holds a value"
        assert _is_null_anyref(c.table.get(c.store, slot_b)), "slot_b still holds a value"
        # The free list must hand exactly these slots back (LIFO order).
        assert c._invoke1("__externref_table_alloc") == slot_b
        assert c._invoke1("__externref_table_alloc") == slot_a
    finally:
        c.close()


def test_encode_signed_transaction(wasm: Client, wallet: Wallet, unsigned_tx) -> None:
    inp, out, tx = unsigned_tx
    witness = witness_for(wasm, wallet, inp, out, tx)
    signed = wasm.encode_signed_transaction(tx, witness)
    assert len(signed) > len(tx)


def test_encode_partially_signed_transaction(wasm: Client, wallet: Wallet, unsigned_tx) -> None:
    inp, out, tx = unsigned_tx
    witness = witness_for(wasm, wallet, inp, out, tx)
    pst = wasm.encode_partially_signed_transaction(
        tx,
        b"\x01" + witness,  # Option<InputWitness>::Some
        b"\x01" + out,  # Option<TxOutput>::Some
        b"\x01" + wasm.encode_destination(wallet.addr, Network.MAINNET),
        b"\x00",  # Option<HtlcSecret>::None (one per input)
        TxAdditionalInfo(),
        Network.MAINNET,
    )
    assert len(pst) > 0


def test_decode_signed_transaction_to_js(wasm: Client, wallet: Wallet, unsigned_tx) -> None:
    inp, out, tx = unsigned_tx
    signed = wasm.encode_signed_transaction(tx, witness_for(wasm, wallet, inp, out, tx))
    decoded = wasm.decode_signed_transaction_to_js(signed, Network.MAINNET)
    assert b"transaction" in decoded
    assert decoded[:1] == b"{"


def test_decode_partially_signed_transaction_to_js(
    wasm: Client, wallet: Wallet, unsigned_tx
) -> None:
    inp, out, tx = unsigned_tx
    witness = witness_for(wasm, wallet, inp, out, tx)
    pst = wasm.encode_partially_signed_transaction(
        tx,
        b"\x01" + witness,
        b"\x01" + out,
        b"\x01" + wasm.encode_destination(wallet.addr, Network.MAINNET),
        b"\x00",
        TxAdditionalInfo(),
        Network.MAINNET,
    )
    decoded = wasm.decode_partially_signed_transaction_to_js(pst, Network.MAINNET)
    assert b'"type":"V1"' in decoded
    assert b'"tx"' in decoded


def test_decode_garbage_raises(wasm: Client) -> None:
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.decode_signed_transaction_to_js(b"\x00" * 8, Network.MAINNET)
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.decode_partially_signed_transaction_to_js(b"\x00" * 8, Network.MAINNET)


def test_extract_htlc_secret_no_htlc_raises(wasm: Client, wallet: Wallet, unsigned_tx) -> None:
    inp, out, tx = unsigned_tx
    signed = wasm.encode_signed_transaction(tx, witness_for(wasm, wallet, inp, out, tx))
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.extract_htlc_secret(signed, True, b"\x02" * 32, 0)


def test_internal_verify_witness_ok(wasm: Client, wallet: Wallet, unsigned_tx) -> None:
    inp, out, tx = unsigned_tx
    witness = witness_for(wasm, wallet, inp, out, tx)
    wasm.internal_verify_witness(
        int(SignatureHashType.SIGHASH_ALL),
        wallet.addr,
        witness,
        tx,
        b"\x01" + out,
        0,
        TxAdditionalInfo(),
        100,
        Network.MAINNET,
    )


def test_internal_verify_witness_wrong_input_index(
    wasm: Client, wallet: Wallet, unsigned_tx
) -> None:
    inp, out, tx = unsigned_tx
    witness = witness_for(wasm, wallet, inp, out, tx)
    with pytest.raises(WasmError, match="^mintlayer: "):
        wasm.internal_verify_witness(
            int(SignatureHashType.SIGHASH_ALL),
            wallet.addr,
            witness,
            tx,
            b"\x01" + out,
            1,  # transaction has a single input (index 0)
            TxAdditionalInfo(),
            100,
            Network.MAINNET,
        )
