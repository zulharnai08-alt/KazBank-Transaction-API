"""Send 20 concurrent GET requests and display shared pool statistics."""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:5000"


def get_json(path: str):
    started = time.perf_counter()
    request = Request(f"{BASE_URL}{path}", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, time.perf_counter() - started, payload
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, time.perf_counter() - started, {"error": body}
    except (URLError, TimeoutError) as exc:
        return 0, time.perf_counter() - started, {"error": str(exc)}


def main():
    print("===== CONNECTION POOL LOAD TEST =====")

    before_status, _, before = get_json("/health")
    print("Health before load:", before_status)
    print("Pool stats before load:", before.get("pool_stats", before))

    results = []
    # 20 одновременных запросов к API, который получает соединения из общего пула.
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(get_json, "/customers") for _ in range(20)]
        for future in as_completed(futures):
            results.append(future.result())

    success_count = sum(1 for status, _, _ in results if status == 200)
    failed_count = len(results) - success_count
    avg_ms = (
        sum(elapsed for _, elapsed, _ in results) / len(results) * 1000
        if results else 0
    )

    print("Concurrent requests:", len(results))
    print("Successful requests:", success_count)
    print("Failed requests:", failed_count)
    print(f"Average response time: {avg_ms:.2f} ms")

    after_status, _, after = get_json("/health")
    print("Health after load:", after_status)
    stats = after.get("pool_stats", {})
    print("Pool stats after load:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

    if before_status == 200 and after_status == 200 and success_count == 20:
        print("PASS: all 20 concurrent requests completed using the shared pool.")
    else:
        print("CHECK: review the failed requests and Flask terminal output.")


if __name__ == "__main__":
    main()
