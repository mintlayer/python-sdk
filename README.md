# Mintlayer Python SDK

A Python SDK for the [Mintlayer](https://www.mintlayer.org/) blockchain.

```
pip install mintlayer
```

Requires Python 3.10+. The WASM cryptography runtime is bundled with the package.

> Work in progress — ported from the [Mintlayer Go SDK](https://github.com/mintlayer/go-sdk).

## Documentation

| Guide | Description |
|-------|-------------|
| [docs/indexer.md](docs/indexer.md) | Full indexer client reference |
| [docs/node.md](docs/node.md) | Full node client reference |
| [docs/wallet.md](docs/wallet.md) | Full wallet client reference |
| [docs/wasm.md](docs/wasm.md) | Full WASM client reference |
| [docs/transactions.md](docs/transactions.md) | Building and signing transactions without the wallet daemon |
| [docs/staking.md](docs/staking.md) | Staking pools and delegations |
| [docs/tokens.md](docs/tokens.md) | Fungible token and NFT lifecycle |

## Overview

The SDK is organised as four independent sub-clients plus a top-level `Client`
that wires them together:

| Module | Purpose | Default port |
|---|---|---|
| `mintlayer.node` | JSON-RPC 2.0 client for the node daemon | 3030 (mainnet) |
| `mintlayer.indexer` | REST client for the indexer (api-web-server) | 3000 |
| `mintlayer.wallet` | JSON-RPC 2.0 client for the wallet daemon | 3034 (mainnet) |
| `mintlayer.wasm` | Cryptography & transaction-building via WASM | — |

## Quick start

```python
import mintlayer

client = mintlayer.Client(mintlayer.Config(
    node_url="http://127.0.0.1:3030",
    indexer_url="http://127.0.0.1:3000",
    wallet_url="http://127.0.0.1:3034",
))

tip = client.indexer.get_tip()
print(f"chain tip: height={tip.block_height} id={tip.block_id}")

client.init_wasm()
priv_key = client.wasm.make_private_key()
```

## License

MIT — see [LICENSE](LICENSE).
