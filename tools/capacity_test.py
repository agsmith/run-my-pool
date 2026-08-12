#!/usr/bin/env python3
"""Small dependency-free HTTP capacity test for Run My Pool."""

import argparse
import concurrent.futures
import json
import random
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request


def percentile(values, percent):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percent / 100)))
    return ordered[index]


def request_once(base_url, path, token, timeout):
    started = time.monotonic()
    request = urllib.request.Request(urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/")))
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    except Exception:
        status = 0
    return status, (time.monotonic() - started) * 1000


def run_user(deadline, rate, base_url, paths, token, timeout):
    results = []
    interval = 1 / rate
    while time.monotonic() < deadline:
        started = time.monotonic()
        path = random.choice(paths)
        status, latency = request_once(base_url, path, token, timeout)
        results.append((path, status, latency))
        time.sleep(max(0, interval - (time.monotonic() - started)))
    return results


def main():
    parser = argparse.ArgumentParser(description="Run a bounded Run My Pool capacity test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--token", help="Bearer token for authenticated scenarios")
    parser.add_argument("--pool-id", help="Pool used for authenticated dashboard traffic")
    parser.add_argument("--users", type=int, default=50, help="Concurrent simulated users")
    parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    parser.add_argument("--rate", type=float, default=1, help="Requests per second per simulated user")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--max-p95-ms", type=float, default=750)
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--confirm-production", action="store_true")
    args = parser.parse_args()

    if "runmypool.net" in args.base_url and not args.confirm_production:
        parser.error("Production tests require --confirm-production")
    if args.users < 1 or args.users > 250:
        parser.error("--users must be between 1 and 250")
    if args.rate <= 0 or args.rate > 5:
        parser.error("--rate must be greater than 0 and no more than 5")

    paths = ["/health", "/schedule/week/1", "/schedule/week/2"]
    if args.token and args.pool_id:
        paths.extend([
            "/pools/my-pools",
            f"/pools/{args.pool_id}/activity-summary?week=1",
            f"/pools/{args.pool_id}/lock-status",
        ])

    deadline = time.monotonic() + args.duration
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.users) as executor:
        futures = [
            executor.submit(run_user, deadline, args.rate, args.base_url, paths, args.token, args.timeout)
            for _ in range(args.users)
        ]
        for future in concurrent.futures.as_completed(futures):
            results.extend(future.result())

    latencies = [latency for _, _, latency in results]
    failures = sum(status < 200 or status >= 400 for _, status, _ in results)
    error_rate = failures / len(results) if results else 1.0
    summary = {
        "requests": len(results),
        "concurrent_users": args.users,
        "requests_per_second": round(len(results) / args.duration, 2),
        "error_rate": round(error_rate, 4),
        "latency_ms": {
            "mean": round(statistics.fmean(latencies), 2) if latencies else 0,
            "p50": round(percentile(latencies, 50), 2),
            "p95": round(percentile(latencies, 95), 2),
            "p99": round(percentile(latencies, 99), 2),
        },
        "endpoints": {},
    }
    for path in sorted(set(path for path, _, _ in results)):
        endpoint_results = [(status, latency) for result_path, status, latency in results if result_path == path]
        endpoint_latencies = [latency for _, latency in endpoint_results]
        endpoint_failures = sum(status < 200 or status >= 400 for status, _ in endpoint_results)
        summary["endpoints"][path] = {
            "requests": len(endpoint_results),
            "error_rate": round(endpoint_failures / len(endpoint_results), 4),
            "p50_ms": round(percentile(endpoint_latencies, 50), 2),
            "p95_ms": round(percentile(endpoint_latencies, 95), 2),
        }
    print(json.dumps(summary, indent=2))
    raise SystemExit(1 if error_rate > args.max_error_rate or percentile(latencies, 95) > args.max_p95_ms else 0)


if __name__ == "__main__":
    main()
