"""WASM cryptography and transaction-building client.

Mirrors go-sdk/wasm/client.go: instantiates the embedded ``wasm_wrappers_bg``
module with a wasm-bindgen host shim and exposes the full API surface as
methods. The core machinery lives in :mod:`mintlayer.wasm._core`; the per-area
method groups (keys, addresses, …) are mixins, combined here into ``Client``.
"""

from __future__ import annotations

from .addresses import AddressesMixin
from .fees import FeesMixin
from .ids import IdsMixin
from .inputs import InputsMixin
from .intent import IntentMixin
from .keys import KeysMixin
from .outputs import OutputsMixin
from .signing import SigningMixin
from .staking import StakingMixin
from .timelocks import TimelocksMixin
from .transactions import TransactionsMixin


class Client(
    KeysMixin,
    AddressesMixin,
    IdsMixin,
    InputsMixin,
    OutputsMixin,
    TimelocksMixin,
    FeesMixin,
    TransactionsMixin,
    SigningMixin,
    StakingMixin,
    IntentMixin,
):
    """Provides access to all Mintlayer WASM functions.

    A ``Client`` is safe for concurrent use from multiple threads; every
    public method serialises access to the single WASM instance.
    """
