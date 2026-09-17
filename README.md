# Mintlayer Python SDK

A Python SDK for the [Mintlayer](https://www.mintlayer.org/) blockchain,
ported from the [Mintlayer Go SDK](https://github.com/mintlayer/go-sdk).

```
pip install mintlayer
```

Requires Python 3.10+. The WASM cryptography runtime (wasmtime) is bundled
with the package.

---

## Documentation

| Guide | Description |
|-------|-------------|
| [docs/indexer.md](docs/indexer.md) | Full indexer client reference: chain, blocks, transactions, addresses, pools, tokens, orders, statistics |
| [docs/node.md](docs/node.md) | Full node client reference: chainstate, mempool, P2P, block submission |
| [docs/wallet.md](docs/wallet.md) | Full wallet client reference: lifecycle, accounts, balances, transactions |
| [docs/wasm.md](docs/wasm.md) | Full WASM client reference: keys, addresses, inputs, outputs, signing, fees |
| [docs/transactions.md](docs/transactions.md) | Step-by-step guide to building and signing transactions without the wallet daemon |
| [docs/staking.md](docs/staking.md) | Staking pools and delegations: creation, funding, withdrawal, and read queries |
| [docs/tokens.md](docs/tokens.md) | Fungible token and NFT lifecycle: issuance, minting, freezing, authority, manual encoding |

---

## Overview

The SDK is organised as four independent sub-clients plus a top-level `Client`
that wires them together.

| Module | Purpose | Default port |
|---|---|---|
| `mintlayer.node` | JSON-RPC 2.0 client for the node daemon | 3030 (mainnet) |
| `mintlayer.indexer` | REST client for the indexer (api-web-server) | 3000 |
| `mintlayer.wallet` | JSON-RPC 2.0 client for the wallet daemon | 3034 (mainnet) |
| `mintlayer.wasm` | Cryptography & transaction-building via WASM | — |

Use the top-level client when you need multiple sub-clients, or import
sub-modules directly when you only need one.

---

## Quick start

```python
import mintlayer

client = mintlayer.Client(
    mintlayer.Config(
        node_url="http://127.0.0.1:3030",
        indexer_url="http://127.0.0.1:3000",
        wallet_url="http://127.0.0.1:3034",
    )
)

# Query the chain tip from the indexer.
tip = client.indexer.get_tip()
print(f"chain tip: height={tip.block_height} id={tip.block_id}")

# Optionally initialise the embedded WASM cryptography runtime (~400 ms).
# The first access triggers lazy construction; init_wasm() makes the cost
# explicit and is a no-op afterwards.
client.init_wasm()

priv_key = client.wasm.make_private_key()
pub_key = client.wasm.public_key_from_private_key(priv_key)
addr = client.wasm.pubkey_to_pubkeyhash_address(pub_key, mintlayer.MAINNET)
print("address:", addr)

client.close()  # or use `with mintlayer.Client(cfg) as client:`
```

`Config` only constructs the sub-clients whose URL field is non-empty
(`node_url`, `indexer_url`, `wallet_url`, plus shared `username`, `password`,
`timeout`).

---

## Node client (`mintlayer.node`)

JSON-RPC 2.0 client for the Mintlayer node daemon. Supports Basic Auth for
nodes with authentication enabled.

```python
from mintlayer.node import Client

c = Client(
    "http://127.0.0.1:3030",
    username="user",  # optional
    password="pass",  # optional
    timeout=10.0,  # optional, seconds
)

# Chain state
info = c.chainstate_info()
height = c.best_block_height()
block_id = c.best_block_id()

# Look up a block
block_hex = c.get_block(block_id)
block_json = c.get_block_json(block_id)

# Token / order info
token_info = c.token_info("ttml1...")
order_info = c.order_info("mordr1...")

# Mempool
c.mempool_submit_transaction(signed_tx_hex, "Untrusted")
fee_rate = c.get_fee_rate(1)

# P2P
peer_count = c.get_peer_count()
peers = c.get_connected_peers()
```

Errors from the daemon are raised as `RPCError` with a numeric `code` and
`message`.

---

## Indexer client (`mintlayer.indexer`)

REST client for `api-web-server`. All paths are relative to `/api/v2`.

```python
from mintlayer.indexer import Client, PageOpts, PoolListOpts

c = Client("http://127.0.0.1:3000", timeout=15.0)

# Chain
tip = c.get_tip()
block_id_at_height = c.get_block_id_at_height(100_000)

# Block
block = c.get_block("00000000...")
tx_ids = c.get_block_transaction_ids("00000000...")

# Transaction
tx = c.get_transaction("aabbcc...")
tx_id = c.submit_transaction(signed_tx_hex)  # requires --enable-post-routes

# Address
utxos = c.get_spendable_utxos("mtc1q...")
info = c.get_address_info("mtc1q...")

# Pool / staking
pools = c.list_pools(PoolListOpts(sort="by_pledge"))
pool = c.get_pool("mpool1...")

# Tokens
token = c.get_token("ttml1...")
tokens = c.find_tokens_by_ticker("MYTOKEN", PageOpts(items=10))

# Orders
orders = c.list_orders(PageOpts(offset=0, items=20))
order = c.get_order("mordr1...")

# Statistics
stats = c.get_coin_statistics()
```

Non-2xx responses are raised as `HTTPError` with a `status_code` and `body`.

---

## Wallet client (`mintlayer.wallet`)

JSON-RPC 2.0 client for `wallet-rpc-daemon`. The wallet daemon manages key
storage, signing, and broadcasting.

```python
from mintlayer.wallet import (
    Amount,
    ComposeParams,
    Client,
    IssueTokenParams,
    MintParams,
    SendParams,
    TokenMetadata,
    TokenSupply,
)

c = Client("http://127.0.0.1:3034", username="user", password="pass")

# Wallet lifecycle
c.open_wallet("/path/to/wallet.dat", password="")
c.sync_wallet()

# Accounts and addresses
info = c.get_wallet_info()
addr = c.new_address(0)  # account 0
balance = c.get_balance(0)

# Send coins (account 0, auto fee)
result = c.address_send(
    SendParams(
        account=0,
        address="mtc1q...",
        amount=Amount(atoms="100000000000"),  # 1 ML
    )
)
print("tx id:", result.tx_id)

# Token operations
issue_result = c.issue_token(
    IssueTokenParams(
        account=0,
        destination_address=addr,
        metadata=TokenMetadata(
            token_ticker="MYTOKEN",
            number_of_decimals=2,
            metadata_uri="https://example.com/token",
            token_supply=TokenSupply(type="Lockable"),
            is_freezable=False,
        ),
    )
)
mint_result = c.mint_tokens(
    MintParams(
        account=0,
        token_id=issue_result.token_id,
        address=addr,
        amount=Amount(atoms="1000"),
    )
)

# Staking
c.start_staking(0)
pools = c.list_owned_pools(0)

# Compose and sign a raw transaction (cold wallet flow)
composed = c.compose_transaction(ComposeParams(...))
signed = c.sign_raw_transaction(0, composed.hex)
submit_result = c.submit_transaction(signed.hex)

c.close_wallet()
```

---

## WASM client (`mintlayer.wasm`)

Cryptographic primitives and binary transaction encoding via an embedded
WebAssembly module. Instantiation takes ~400 ms; create the client once per
process.

```python
from mintlayer.wasm import (
    Amount,
    SOURCE_TRANSACTION,
    SIGHASH_ALL,
    Network,
    TxAdditionalInfo,
)
from mintlayer.wasm import Client as WasmClient

c = WasmClient()

# Key derivation (BIP-44 path 44'/mintlayer_coin_type'/0')
mnemonic = (
    "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
)
account_key = c.make_default_account_privkey(mnemonic, Network.MAINNET)
recv_key = c.make_receiving_address(account_key, 0)
pub_key = c.public_key_from_private_key(recv_key)
addr = c.pubkey_to_pubkeyhash_address(pub_key, Network.MAINNET)

# Transaction building
src_id = c.encode_outpoint_source_id(tx_id_bytes, SOURCE_TRANSACTION)
input_ = c.encode_input_for_utxo(src_id, output_index)

output = c.encode_output_transfer(
    Amount(atoms="100000000000"),  # 1 ML
    dest_addr,
    Network.MAINNET,
)

tx = c.encode_transaction(input_, output, 0)  # flags = 0
tx_id = c.get_transaction_id(tx, True)

# Signing
witness = c.encode_witness(
    SIGHASH_ALL,
    recv_key,
    addr,
    tx,
    utxo_bytes,  # see docs/transactions.md for the encoding details
    0,  # input index
    TxAdditionalInfo(),
    block_height,
    Network.MAINNET,
)
signed_tx = c.encode_signed_transaction(tx, witness)

c.close()
```

See [examples/send_coins.py](examples/send_coins.py) for a complete end-to-end
transaction flow, and [docs/transactions.md](docs/transactions.md) for the full
walkthrough.

---

## Top-level client

`mintlayer.Client` constructs only the sub-clients whose URL is non-empty.

```python
# Node + WASM only — no wallet or indexer client is created.
client = mintlayer.Client(
    mintlayer.Config(
        node_url="http://127.0.0.1:3030",
        username="user",
        password="pass",
    )
)

# Call init_wasm() before using client.wasm (raises WasmError otherwise).
client.init_wasm()
```

Convenience re-exports (`mintlayer.Amount`, `mintlayer.Network`,
`mintlayer.MAINNET`, …) mirror the Go SDK's aliases, so callers that only
import the top-level package do not need to also import `mintlayer.wasm`.

---

## Examples

| Example | Description |
|---|---|
| [examples/send_coins.py](examples/send_coins.py) | Derive key → fetch UTXOs → build, sign, and submit a transaction |
| [examples/issue_token.py](examples/issue_token.py) | Issue a fungible token and mint an initial supply via the wallet daemon |

---

## Amounts

All coin and token amounts use the `Amount` type, which stores the value as a
decimal string of _atoms_ — the smallest indivisible unit. **1 ML =
100,000,000,000 atoms** (11 decimal places).

```python
from mintlayer.wasm import Amount

one = Amount.from_atoms("100000000000")  # 1 ML
zero = Amount.zero()
print(one.atoms)  # "100000000000"
```

The indexer and wallet clients use their own `Amount` dataclass with both
`atoms` and `decimal` fields populated by the server.

---

## Networks

| Constant | Value | Use |
|---|---|---|
| `MAINNET` | 0 | Production network |
| `TESTNET` | 1 | Public test network |
| `REGTEST` | 2 | Local regression testing |
| `SIGNET` | 3 | Signet |

Pass the network constant (`mintlayer.Network` enum members or the
module-level aliases) to any function that derives addresses or encodes
transactions.

---

## Error handling

- `mintlayer.node.RPCError` — JSON-RPC error from the node daemon (`code`,
  `message`); transport failures raise `JSONRPCError`
- `mintlayer.wallet.RPCError` — JSON-RPC error from the wallet daemon
- `mintlayer.indexer.HTTPError` — non-2xx HTTP response from the indexer
  (`status_code`, `body`); transport failures raise `IndexerError`
- `mintlayer.wasm.WasmError` — WASM operation failures, with a message
  prefixed by `mintlayer:`

---

## License

MIT — see [LICENSE](LICENSE).
