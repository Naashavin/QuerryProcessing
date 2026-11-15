import json
import statistics
import time
from contextlib import closing
from pathlib import Path
from db_config import BASE_DIR, get_connection
from dialect import Dialect
from seed_data import seed_database


def is_reachable(db_type):
    if db_type == "sqlite":
        return True
    try:
        with closing(get_connection(db_type)):
            return True
    except Exception:
        return False


def measure_op(fn, repeats=3):
    timings = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        timings.append((time.perf_counter() - t0) * 1000.0)
    mean_ms = statistics.mean(timings)
    spread_ms = max(timings) - min(timings)
    return {
        "runs_ms": [round(x, 2) for x in timings],
        "mean_ms": round(mean_ms, 2),
        "spread_ms": round(spread_ms, 2),
    }


def benchmark_database(db_type):
    d = Dialect(db_type)
    seed_database(db_type, seed=42)

    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT member_id FROM member ORDER BY member_id LIMIT 20")
        mids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT book_id FROM book ORDER BY book_id LIMIT 40")
        bids = [r[0] for r in cur.fetchall()]

        ins_sql = d.sql("INSERT INTO loan (member_id, book_id, issued_on, due_on) VALUES ({ph}, {ph}, {ph}, {ph})")

        # (a) 1,000 loans with commit after each row (3 runs)
        def op_per_row_commit():
            cur.execute("DELETE FROM loan WHERE issued_on = '2026-12-01'")
            conn.commit()
            for i in range(1000):
                cur.execute(ins_sql, (mids[i % len(mids)], bids[i % len(bids)], "2026-12-01", "2026-12-15"))
                conn.commit()

        # (b) 1,000 loans via executemany in one commit (3 runs)
        batch_1k = [(mids[i % len(mids)], bids[i % len(bids)], "2026-12-02", "2026-12-16") for i in range(1000)]

        def op_executemany():
            cur.execute("DELETE FROM loan WHERE issued_on = '2026-12-02'")
            conn.commit()
            cur.executemany(ins_sql, batch_1k)
            conn.commit()

        # Prepare >= 5,000 loans for query (c), update (d), delete (e)
        batch_5k = [(mids[i % len(mids)], bids[i % len(bids)], "2026-12-03", "2026-12-17") for i in range(5000)]
        cur.executemany(ins_sql, batch_5k)
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM loan")
        total_loans = cur.fetchone()[0]

        join_sql = (
            "SELECT m.member_code, b.category_id, COUNT(l.loan_id) AS cnt "
            "FROM loan l JOIN member m ON l.member_id = m.member_id "
            "JOIN book b ON l.book_id = b.book_id "
            "GROUP BY m.member_code, b.category_id ORDER BY cnt DESC"
        )

        def op_join_query():
            cur.execute(join_sql)
            cur.fetchall()

        res_a = measure_op(op_per_row_commit, repeats=3)
        res_b = measure_op(op_executemany, repeats=3)
        res_c1 = measure_op(op_join_query, repeats=3)

        # Create composite index and repeat query (c)
        cur.execute("CREATE INDEX idx_loan_mem_book ON loan(member_id, book_id)")
        conn.commit()
        res_c2 = measure_op(op_join_query, repeats=3)

        # (d) Update 500 rows (3 runs)
        cur.execute("SELECT loan_id FROM loan ORDER BY loan_id DESC LIMIT 500")
        target_ids = [r[0] for r in cur.fetchall()]
        min_id, max_id = min(target_ids), max(target_ids)

        def op_update_500():
            cur.execute(
                d.sql("UPDATE loan SET renew_count = 1 WHERE loan_id BETWEEN {ph} AND {ph}"),
                (min_id, max_id),
            )
            conn.commit()

        res_d = measure_op(op_update_500, repeats=3)

        # (e) Delete 500 rows (re-insert 500 rows before timing delete cleanly across 3 runs)
        batch_500 = [(mids[i % len(mids)], bids[i % len(bids)], "2026-12-05", "2026-12-19") for i in range(500)]

        def op_delete_500():
            cur.executemany(ins_sql, batch_500)
            conn.commit()
            t0 = time.perf_counter()
            cur.execute("DELETE FROM loan WHERE issued_on = '2026-12-05'")
            conn.commit()
            return (time.perf_counter() - t0) * 1000.0

        del_times = [op_delete_500() for _ in range(3)]
        res_e = {
            "runs_ms": [round(x, 2) for x in del_times],
            "mean_ms": round(statistics.mean(del_times), 2),
            "spread_ms": round(max(del_times) - min(del_times), 2),
        }

        cur.close()

    return {
        "db_type": db_type,
        "loans_in_table_for_join": total_loans,
        "a_1000_commits": res_a,
        "b_1000_executemany": res_b,
        "c1_join_before_index": res_c1,
        "c2_join_after_index": res_c2,
        "d_update_500": res_d,
        "e_delete_500": res_e,
    }


def main():
    results = {}
    for db_type in ("sqlite", "mysql", "postgres"):
        if not is_reachable(db_type):
            print(f"[{db_type.upper()}] Skipped benchmark — server not running locally.")
            continue
        print(f"Running benchmark on {db_type.upper()}...")
        results[db_type] = benchmark_database(db_type)

    out_path = BASE_DIR / "logs" / "benchmark_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("\n=== Benchmark Summary (Mean ms / Spread ms across 3 runs) ===")
    for dbt, res in results.items():
        print(f"\n[{dbt.upper()}] (Join rows={res['loans_in_table_for_join']})")
        for key in ("a_1000_commits", "b_1000_executemany", "c1_join_before_index", "c2_join_after_index", "d_update_500", "e_delete_500"):
            st = res[key]
            print(f"  {key:<22}: mean={st['mean_ms']:>8.2f} ms | spread={st['spread_ms']:>6.2f} ms | runs={st['runs_ms']}")


if __name__ == "__main__":
    main()

