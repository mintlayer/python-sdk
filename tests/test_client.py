"""Tests for the top-level SDK client (mintlayer.client).

Mirrors the construction/config sections of go-sdk/client.go usage: which
sub-clients get built from a Config, basic-auth wiring, the lazy WASM
runtime, and the package-level convenience re-exports.
"""

from __future__ import annotations

import base64
import importlib

import pytest

import mintlayer
from mintlayer.client import Client, Config
from mintlayer.indexer import Client as IndexerClient
from mintlayer.node import Client as NodeClient
from mintlayer.wallet import BestBlock
from mintlayer.wallet import Client as WalletClient
from mintlayer.wasm import Client as WasmClient
from mintlayer.wasm import WasmError

_BLOCK_RESULT = {"height": 100, "id": "aabbccdd"}


class TestConfigConstruction:
    def test_node_only_config(self) -> None:
        client = Client(Config(node_url="http://127.0.0.1:3030"))
        assert client.node is not None
        assert client.indexer is None
        assert client.wallet is None
        client.close()

    def test_full_config_constructs_sub_clients(self) -> None:
        cfg = Config(
            node_url="http://127.0.0.1:3030",
            indexer_url="http://127.0.0.1:3000",
            wallet_url="http://127.0.0.1:3034",
            username="alice",
            password="secret",
            timeout=5.0,
        )
        client = Client(cfg)
        assert isinstance(client.node, NodeClient)
        assert isinstance(client.indexer, IndexerClient)
        assert isinstance(client.wallet, WalletClient)
        # Basic-auth credentials flow into the JSON-RPC sub-clients.
        assert client.node._rpc.endpoint == "http://127.0.0.1:3030"
        assert client.node._rpc.username == "alice"
        assert client.node._rpc.password == "secret"
        assert client.node._rpc.timeout == 5.0
        assert client.wallet._rpc.endpoint == "http://127.0.0.1:3034"
        assert client.wallet._rpc.username == "alice"
        assert client.wallet._rpc.password == "secret"
        # The indexer is plain REST (IndexerHTTP base): /api/v2 prefix + timeout.
        assert client.indexer.api_base == "http://127.0.0.1:3000/api/v2"
        assert client.indexer.timeout == 5.0
        client.close()

    def test_empty_config_constructs_nothing(self) -> None:
        client = Client(Config())
        assert client.node is None
        assert client.indexer is None
        assert client.wallet is None
        client.close()


def test_basic_auth_reaches_the_wire(rpc_server) -> None:
    """A wallet call through the top-level client sends the Basic auth header."""
    srv = rpc_server(result=_BLOCK_RESULT)
    client = Client(
        Config(node_url=srv.url, wallet_url=srv.url, username="alice", password="secret")
    )
    assert client.wallet.best_block() == BestBlock(height=100, id="aabbccdd")
    expected = "Basic " + base64.b64encode(b"alice:secret").decode("ascii")
    assert srv.capture.headers.get("authorization") == expected
    client.close()


class TestWasmLifecycle:
    def test_wasm_raises_before_init(self) -> None:
        client = Client(Config(node_url="http://127.0.0.1:3030"))
        with pytest.raises(WasmError, match="init_wasm"):
            _ = client.wasm
        client.close()

    def test_init_wasm_creates_client_and_close_releases_it(self) -> None:
        """init_wasm() builds a real WasmClient; close() resets the property."""
        client = Client(Config(node_url="http://127.0.0.1:3030"))
        client.init_wasm()
        wasm = client.wasm
        assert isinstance(wasm, WasmClient)
        # Subsequent init_wasm calls are no-ops (same instance).
        client.init_wasm()
        assert client.wasm is wasm
        client.close()
        assert client._wasm is None
        with pytest.raises(WasmError, match="init_wasm"):
            _ = client.wasm


class TestConfigRedaction:
    def test_repr_redacts_password(self) -> None:
        got = repr(
            Config(
                node_url="http://127.0.0.1:3030",
                indexer_url="http://127.0.0.1:3000",
                wallet_url="http://127.0.0.1:3034",
                username="alice",
                password="hunter2",
                timeout=5.0,
            )
        )
        assert "password='***'" in got
        assert "hunter2" not in got
        # The non-secret fields stay visible for debugging.
        assert "node_url='http://127.0.0.1:3030'" in got
        assert "indexer_url='http://127.0.0.1:3000'" in got
        assert "wallet_url='http://127.0.0.1:3034'" in got
        assert "username='alice'" in got
        assert "timeout=5.0" in got

    def test_password_field_has_repr_disabled(self) -> None:
        """The dataclass field itself is marked repr=False (belt to the braces)."""
        assert Config.__dataclass_fields__["password"].repr is False


class TestCloseClosesSubClients:
    def test_close_closes_each_sub_clients_session(
        self, rpc_server, rest_server, monkeypatch
    ) -> None:
        """Top-level close() must reach the HTTP session each sub-client owns."""
        node_srv = rpc_server(result=_BLOCK_RESULT)
        indexer_srv = rest_server(payload={})
        wallet_srv = rpc_server(result=None)
        client = Client(
            Config(
                node_url=node_srv.url,
                indexer_url=indexer_srv.url,
                wallet_url=wallet_srv.url,
            )
        )
        closed: list[str] = []
        monkeypatch.setattr(client.node._rpc._session, "close", lambda: closed.append("node"))
        monkeypatch.setattr(client.indexer._session, "close", lambda: closed.append("indexer"))
        monkeypatch.setattr(client.wallet._rpc._session, "close", lambda: closed.append("wallet"))
        client.close()
        # Node, indexer and wallet are all released, in construction order.
        assert closed == ["node", "indexer", "wallet"]

    def test_close_is_idempotent_with_sub_clients(self, rpc_server) -> None:
        """A second close() with real sub-clients must not raise."""
        client = Client(Config(node_url=rpc_server(result=_BLOCK_RESULT).url))
        client.close()
        client.close()


class TestContextManager:
    def test_with_block_and_idempotent_close(self) -> None:
        with mintlayer.Client(mintlayer.Config(node_url="http://127.0.0.1:3030")) as c:
            assert isinstance(c, Client)
            assert c.node is not None
        # close() is idempotent -- no WASM runtime, nothing to release.
        c.close()
        c.close()


class TestPackageReExports:
    def test_amount_reexport(self) -> None:
        assert mintlayer.Amount.from_atoms("5").atoms == "5"

    def test_network_constants(self) -> None:
        assert mintlayer.MAINNET == mintlayer.Network.MAINNET
        assert mintlayer.TESTNET == mintlayer.Network.TESTNET

    def test_sighash_and_source_reexports(self) -> None:
        assert mintlayer.SIGHASH_ALL == mintlayer.wasm.SignatureHashType.SIGHASH_ALL
        assert mintlayer.SOURCE_TRANSACTION == mintlayer.wasm.SourceId.SOURCE_TRANSACTION

    def test_wasm_error_reexport(self) -> None:
        assert mintlayer.WasmError is WasmError

    @pytest.mark.parametrize("module_name", ["node", "indexer", "wallet", "wasm"])
    def test_submodules_importable(self, module_name: str) -> None:
        assert importlib.import_module(f"mintlayer.{module_name}") is not None
