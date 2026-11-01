"""Concurrent load test against a running backend (no extra dependencies).

    python -m app.scripts.load_test --url https://your-api.onrender.com \
        --token-file tourist_tokens.txt --concurrency 100 --rounds 5

tourist_tokens.txt holds one tourist bearer token per line (tourists who gave
consent). Reports latency percentiles for concurrent location updates and an
optional SOS burst (--sos, creates real SOS records: test environments only).
"""
from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import time

import httpx


async def run(url: str, tokens: list[str], rounds: int, sos: bool) -> None:
    latencies: list[float] = []
    errors = 0
    async with httpx.AsyncClient(base_url=url, timeout=30) as client:
        async def one(token: str, path: str, body: dict) -> None:
            nonlocal errors
            start = time.perf_counter()
            r = await client.post(path, json=body, headers={"Authorization": f"Bearer {token}"})
            latencies.append((time.perf_counter() - start) * 1000)
            if r.status_code >= 400:
                errors += 1

        for _ in range(rounds):
            await asyncio.gather(*[
                one(t, "/api/v1/me/location", {"latitude": 12.97 + random.random() / 100, "longitude": 77.59 + random.random() / 100, "accuracy": 10})
                for t in tokens
            ])
        if sos:
            await asyncio.gather(*[one(t, "/api/v1/me/sos", {"message": "LOAD TEST", "idempotency_key": f"load-{i}"}) for i, t in enumerate(tokens)])

    q = statistics.quantiles(latencies, n=100)
    print(f"requests={len(latencies)} errors={errors} p50={q[49]:.0f}ms p95={q[94]:.0f}ms max={max(latencies):.0f}ms")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--token-file", required=True)
    p.add_argument("--concurrency", type=int, default=100)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--sos", action="store_true")
    a = p.parse_args()
    tokens = [t.strip() for t in open(a.token_file, encoding="utf-8") if t.strip()][: a.concurrency]
    asyncio.run(run(a.url.rstrip("/"), tokens, a.rounds, a.sos))


if __name__ == "__main__":
    main()
