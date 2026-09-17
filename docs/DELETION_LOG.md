# Code Deletion Log

## 2026-09-17 Refactor Session (DRY cleanup of `mintlayer/`)

### Duplicates Consolidated

- `mintlayer/node/_core.py` + `mintlayer/wallet/_core.py` — the `_call`,
  `_call_ignore` and `close` helpers were duplicated across both packages.
  Hoisted into a shared `BaseJSONRPCClient` mixin base in
  `mintlayer/_jsonrpc.py:112`. `_NodeCore` and `_WalletCore` now subclass it
  and keep only their package-specific typed decoders (`_call_str` /
  `_call_opt_int` / ... vs `_call_model` / `_call_model_list`).
- `mintlayer/indexer/_core.py` (deleted) — `IndexerCore` was a pure
  pass-through over `_http.IndexerHTTP` (`_get` → `get`, `_post_text` →
  `post_text`). The nine endpoint mixins now subclass `IndexerHTTP`
  directly and call the transport methods; the `_seg` path-segment encoder
  moved to `mintlayer/indexer/_http.py:31` next to the URL construction it
  serves.

### Unused Files Deleted

- `mintlayer/indexer/_core.py` — replaced by direct `IndexerHTTP` base class
  (see above).

### Unused Exports Removed

- `mintlayer/indexer/block.py` — dropped the `Transaction` re-export
  (`# noqa: F401`). Nothing imported `Transaction` from this module; the
  public surface path `mintlayer.indexer.Transaction` (via `__init__.py`)
  is unchanged. Go parity check: `go-sdk/indexer/block.go` never touches
  `Transaction`.
- `mintlayer/node/client.py` / `mintlayer/wallet/client.py` — removed the
  redundant `# noqa: F401` markers on the `JSONRPCError` imports; both
  modules list it in `__all__`, so the suppression was dead (RUF100 not
  enabled, hence undetected by lint).
- `mintlayer/node/_core.py` — replaced the function-local
  `from .types import Amount` inside `_call_opt_amount` with a module-level
  import (no cycle: `node/types.py` has no intra-package imports), and
  tightened the return annotation `Any` → `Amount | None`.

### Deliberately Left Alone

- `from_json`/`to_json` boilerplate in `node|indexer|wallet/types.py` —
  explicit field-by-field wire mapping mirrors the Go structs; wire-format
  fidelity beats DRY here.
- WASM mixins (`mintlayer/wasm/`) — 1:1 mapping to Go files/exports is
  intentional; audited for dead branches, none found.

### Impact

- Files deleted: 1
- Net lines removed: 33 (6133 → 6100; +93/−126)
- Public API surface: unchanged (all `__init__.py` re-exports intact)

### Testing

- `uv run pytest tests/ -q` → 238 passed (zero test modifications)
- `uv run ruff check .` → All checks passed
- `uv run ruff format mintlayer/` → 50 files already formatted
- `uv run mypy mintlayer/` → no issues found in 50 source files
