import json
import time
import tracemalloc
from config import RAW_JSONL_PATH


def test_original_json_load():
    """D1 Observation: feed Source D (.jsonl) directly to original json.load() assumption."""
    try:
        with open(RAW_JSONL_PATH, "r", encoding="utf-8") as f:
            json.load(f)
        print("D1 Observation: Unexpectedly succeeded")
    except json.JSONDecodeError as err:
        print(f"D1 Observation: Original json.load() CRASHED -> {type(err).__name__}: {err}")


def benchmark_bulk_vs_streaming():
    """D2 Evidence: compare bulk in-memory JSON list loading vs line-by-line streaming on 20,000+ lines."""
    # 1. Bulk in-memory load (loading all valid JSON lines into one Python list)
    tracemalloc.start()
    t0 = time.perf_counter()
    records = []
    bulk_errors = 0
    with open(RAW_JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                bulk_errors += 1
    # Simulate flattening pass over in-memory list
    bulk_valid = sum(1 for r in records if r.get("session_id"))
    bulk_time_ms = (time.perf_counter() - t0) * 1000.0
    _, bulk_peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del records

    # 2. Streaming line-by-line (O(1) memory footprint)
    tracemalloc.start()
    t0 = time.perf_counter()
    stream_valid = 0
    stream_errors = 0
    with open(RAW_JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("session_id"):
                    stream_valid += 1
            except json.JSONDecodeError:
                stream_errors += 1
    stream_time_ms = (time.perf_counter() - t0) * 1000.0
    _, stream_peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("\n=== D2 Memory & Timing Comparison (20,100-line Source D) ===")
    print(f"  Bulk In-Memory Load : valid={bulk_valid}, errors={bulk_errors} | time={bulk_time_ms:.2f} ms | peak_mem={bulk_peak_bytes / (1024*1024):.2f} MB")
    print(f"  Line-by-Line Stream : valid={stream_valid}, errors={stream_errors} | time={stream_time_ms:.2f} ms | peak_mem={stream_peak_bytes / (1024*1024):.2f} MB")


if __name__ == "__main__":
    test_original_json_load()
    benchmark_bulk_vs_streaming()

