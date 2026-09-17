"""Security regression tests: repr() must never leak mnemonic/passphrase.

These types carry secrets (BIP-39 mnemonics, wallet passphrases) that end up in
logs via repr()/str() (tracebacks, debug prints, repr of containing objects).
The custom ``__repr__`` implementations render ``<redacted>`` placeholders;
``to_json()`` still carries the real values for the JSON-RPC wire.
"""

from __future__ import annotations

from mintlayer.wallet import (
    CreateWalletParams,
    CreateWalletResult,
    MnemonicResult,
    RecoverWalletParams,
)
from mintlayer.wallet.types import MnemonicContent

_SECRET_MNEMONIC = "secret words"
_SECRET_PASSPHRASE = "pw"


def test_create_wallet_params_repr_redacts_secrets() -> None:
    got = repr(
        CreateWalletParams(
            path="x",
            store_seed_phrase=False,
            mnemonic=_SECRET_MNEMONIC,
            passphrase=_SECRET_PASSPHRASE,
        )
    )
    assert "<redacted>" in got
    assert _SECRET_MNEMONIC not in got
    assert _SECRET_PASSPHRASE not in got


def test_recover_wallet_params_repr_redacts_secrets() -> None:
    got = repr(
        RecoverWalletParams(
            path="x",
            store_seed_phrase=False,
            mnemonic=_SECRET_MNEMONIC,
            passphrase=_SECRET_PASSPHRASE,
        )
    )
    assert got.count("<redacted>") >= 2
    assert _SECRET_MNEMONIC not in got
    assert _SECRET_PASSPHRASE not in got


def test_mnemonic_content_repr_is_fully_redacted() -> None:
    assert repr(MnemonicContent(mnemonic="secret")) == "MnemonicContent(mnemonic='<redacted>')"


def test_create_wallet_result_repr_redacts_nested_mnemonic() -> None:
    """repr of a plain-dataclass container must redact transitively."""
    got = repr(
        CreateWalletResult(
            mnemonic=MnemonicResult(
                type="Bip39",
                content=MnemonicContent(mnemonic=_SECRET_MNEMONIC),
            )
        )
    )
    assert "<redacted>" in got
    assert "MnemonicContent(mnemonic='<redacted>')" in got
    assert _SECRET_MNEMONIC not in got


def test_to_json_still_carries_real_values() -> None:
    """The wire path is unaffected by repr redaction."""
    create = CreateWalletParams(
        path="x",
        store_seed_phrase=False,
        mnemonic=_SECRET_MNEMONIC,
        passphrase=_SECRET_PASSPHRASE,
    )
    recover = RecoverWalletParams(
        path="x",
        store_seed_phrase=False,
        mnemonic=_SECRET_MNEMONIC,
        passphrase=_SECRET_PASSPHRASE,
    )
    assert create.to_json() == {
        "path": "x",
        "store_seed_phrase": False,
        "mnemonic": _SECRET_MNEMONIC,
        "passphrase": _SECRET_PASSPHRASE,
        "hardware_wallet": None,
    }
    assert recover.to_json() == {
        "path": "x",
        "store_seed_phrase": False,
        "mnemonic": _SECRET_MNEMONIC,
        "passphrase": _SECRET_PASSPHRASE,
        "hardware_wallet": None,
    }


def test_repr_unset_secrets_render_as_none_not_placeholder() -> None:
    """Unset optional secrets show None; the placeholder is only for set values."""
    got = repr(CreateWalletParams(path="x", store_seed_phrase=False))
    assert "mnemonic=None" in got
    assert "passphrase=None" in got
    assert got.count("<redacted>") == 0
