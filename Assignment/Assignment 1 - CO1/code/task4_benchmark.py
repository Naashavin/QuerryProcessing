import random
import time
from utils import parse_date


def build_mixed_dates(n=200, seed=42):
    rng = random.Random(seed)
    formats = [
        lambda d, m, y: f"{y:04d}-{m:02d}-{d:02d}",
        lambda d, m, y: f"{d:02d}/{m:02d}/{y:04d}",
        lambda d, m, y: f"{d:02d}-{m:02d}-{y:04d}",
        lambda d, m, y: f"{y:04d}/{m:02d}/{d:02d}",
        lambda d, m, y: f"{d:02d}.{m:02d}.{y:04d}",
    ]
    bad_dates = ["99/99/2026", "not-a-date", "", "2026-13-45", "NA"]
    dates = []
    for i in range(n):
        if i % 20 == 0:
            dates.append(rng.choice(bad_dates))
        else:
            d = rng.randint(1, 28)
            m = rng.randint(1, 12)
            y = rng.randint(1980, 2026)
            dates.append(rng.choice(formats)(d, m, y))
    return dates


def run_benchmark():
    dates = build_mixed_dates(200)
    run_times = []
    unparseable_count = 0
    valid_count = 0

    for run_idx in range(1, 6):
        t0 = time.perf_counter()
        parsed = [parse_date(d) for d in dates]
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        run_times.append(elapsed_ms)
        if run_idx == 1:
            unparseable_count = sum(1 for x in parsed if x is None)
            valid_count = len(parsed) - unparseable_count

    avg_ms = sum(run_times) / len(run_times)
    print(f"Dataset size      : {len(dates)} mixed-format date values")
    print(f"Valid parsed      : {valid_count}")
    print(f"Unparseable count : {unparseable_count}")
    print("Run times (ms)    :", [round(x, 4) for x in run_times])
    print(f"Average time (ms) : {avg_ms:.4f} ms")


if __name__ == "__main__":
    run_benchmark()

