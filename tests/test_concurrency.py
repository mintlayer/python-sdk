"""Concurrent-use test: one client shared by many threads.

Mirrors the "concurrent ID generation" section of go-sdk/node/client_test.go,
additionally asserting that request ids stay unique and increasing.
"""

from __future__ import annotations

import threading

from mintlayer.node import Client


def test_concurrent_calls_unique_increasing_ids(rpc_server) -> None:
    srv = rpc_server(result="1.0.0")
    client = Client(srv.url)
    results: list[str] = []
    errors: list[Exception] = []

    def call() -> None:
        try:
            results.append(client.node_version())
        except Exception as exc:  # noqa: BLE001 - collected and asserted below
            errors.append(exc)

    threads = [threading.Thread(target=call) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert errors == []
    assert results == ["1.0.0"] * 10
    assert srv.capture.request_count == 10
    assert srv.capture.protocol_errors == []

    ids = srv.capture.request_ids
    assert len(set(ids)) == 10, f"expected 10 unique request ids, got {ids}"
    assert sorted(ids) == list(range(1, 11)), f"ids not 1..10: {sorted(ids)}"
    client.close()
