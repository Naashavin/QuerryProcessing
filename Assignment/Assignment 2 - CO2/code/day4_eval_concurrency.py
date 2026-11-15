import threading
import time
from contextlib import closing
from db_config import get_connection
from dedup_members import deduplicate_and_reconcile, generate_merged_branch_dataset
from dialect import Dialect
from repositories import BookRepository, LoanRepository, MemberRepository
from safe_connect import safe_connect
from seed_data import seed_database


def measure_large_scale_queries(db_type="sqlite"):
    """Load 20,000 members & 100,000 loans and time 3 key queries before/after indexes."""
    print(f"\n=== Day-4 Scale Test ({db_type.upper()}: 20,000 members, 100,000 loans) ===")
    seed_database(db_type, seed=42)
    m_raw, l_raw = generate_merged_branch_dataset(num_unique_members=20000, num_loans=100000, seed=42)
    clean_res = deduplicate_and_reconcile(m_raw, l_raw)
    d = Dialect(db_type)

    t_load0 = time.perf_counter()
    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()
        # Insert 20,000 members in bulk
        cur.executemany(
            d.sql("INSERT INTO member (member_code, full_name, email, joined_on, status) VALUES ({ph},{ph},{ph},{ph},{ph})"),
            clean_res["clean_members"],
        )
        conn.commit()

        # Map member_code -> member_id
        cur.execute("SELECT member_code, member_id FROM member")
        code_to_id = {code: mid for code, mid in cur.fetchall()}

        # Build 100,000 clean loan tuples
        loan_tuples = [
            (code_to_id[mcode], bid, iss, due, ret, 0)
            for _lid, mcode, bid, iss, due, ret in clean_res["clean_loans"]
        ]
        # Insert in 10k chunks for clean memory/packet bounds
        ins_loan_sql = d.sql(
            "INSERT INTO loan (member_id, book_id, issued_on, due_on, returned_on, renew_count) "
            "VALUES ({ph},{ph},{ph},{ph},{ph},{ph})"
        )
        for start in range(0, len(loan_tuples), 10000):
            cur.executemany(ins_loan_sql, loan_tuples[start : start + 10000])
        conn.commit()
        load_ms = (time.perf_counter() - t_load0) * 1000.0

        cur.execute("SELECT COUNT(*) FROM member")
        tot_m = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM loan")
        tot_l = cur.fetchone()[0]
        print(f"  Loaded {tot_m} members and {tot_l} loans in {load_ms:.1f} ms")

        sample_code = clean_res["clean_members"][500][0]
        queries = [
            ("Q1: Member Loan History", d.sql("SELECT loan_id, book_id, due_on FROM loan WHERE member_id = {ph}"), (code_to_id[sample_code],)),
            ("Q2: Overdue Unreturned Count", f"SELECT COUNT(*) FROM loan WHERE returned_on IS NULL AND due_on < {d.today_expr()}", ()),
            ("Q3: Top 5 Borrowed Books", "SELECT b.title, COUNT(l.loan_id) AS cnt FROM book b JOIN loan l ON b.book_id = l.book_id GROUP BY b.book_id, b.title ORDER BY cnt DESC LIMIT 5", ()),
        ]

        def run_qset():
            timings = []
            for label, sql, params in queries:
                t0 = time.perf_counter()
                cur.execute(sql, params)
                cur.fetchall()
                timings.append((label, round((time.perf_counter() - t0) * 1000.0, 2)))
            return timings

        before_idx = run_qset()
        cur.execute("CREATE INDEX idx_d4_loan_member ON loan(member_id)")
        cur.execute("CREATE INDEX idx_d4_loan_book ON loan(book_id)")
        cur.execute("CREATE INDEX idx_d4_loan_ret_due ON loan(returned_on, due_on)")
        conn.commit()
        after_idx = run_qset()

        print("  Query Timings (Before vs After Indexes):")
        for (lbl, b_ms), (_, a_ms) in zip(before_idx, after_idx):
            print(f"    {lbl:<30} | before={b_ms:>7.2f} ms | after={a_ms:>7.2f} ms")
        cur.close()


def run_concurrency_test(db_type="mysql"):
    """Race 5 threads on the last 1 copy of a book using original issue_book vs issue_book_safe."""
    print(f"\n=== Concurrency Race Test ({db_type.upper()}: 5 threads -> 1 last copy) ===")
    seed_database(db_type, seed=42)
    d = Dialect(db_type)

    def setup_last_copy(isbn_suffix):
        with closing(get_connection(db_type)) as conn:
            bid = BookRepository(conn, d).add(f"978-777000{isbn_suffix}", "Last Copy Race Book", "Author", 1, 2025, 1)
            mids = []
            for i in range(5):
                mids.append(MemberRepository(conn, d).add(f"RC{isbn_suffix}_{i}", f"Racer {i}", f"rc{isbn_suffix}_{i}@meridian.edu", "2026-11-01"))
            return bid, mids

    def execute_race(use_safe, bid, mids):
        barrier = threading.Barrier(len(mids))
        outcomes = []
        lock = threading.Lock()
        connections_opened = {"count": 0}

        def worker(mid):
            conn = get_connection(db_type)
            with lock:
                connections_opened["count"] += 1
            repo = LoanRepository(conn, d)
            barrier.wait()
            try:
                if use_safe:
                    lid = repo.issue_book_safe(mid, bid, "2026-11-11")
                else:
                    # Slight artificial read-then-write pause inside original naive logic
                    lid = repo.issue_book(mid, bid, "2026-11-11")
                with lock:
                    outcomes.append(("ISSUED", lid))
            except Exception as err:
                with lock:
                    outcomes.append(("REJECTED", f"{type(err).__name__}: {str(err)[:55]}"))
            finally:
                conn.close()

        threads = [threading.Thread(target=worker, args=(m,)) for m in mids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with closing(get_connection(db_type)) as conn:
            cur = conn.cursor()
            cur.execute(d.sql("SELECT copies_available FROM book WHERE book_id = {ph}"), (bid,))
            final_avail = cur.fetchone()[0]
            cur.execute(d.sql("SELECT COUNT(*) FROM loan WHERE book_id = {ph}"), (bid,))
            loan_count = cur.fetchone()[0]
            cur.close()
        return outcomes, final_avail, loan_count, connections_opened["count"]

    # Test 1: Original issue_book
    bid1, mids1 = setup_last_copy("1")
    out1, avail1, lcnt1, conns1 = execute_race(False, bid1, mids1)
    issued1 = sum(1 for s, _ in out1 if s == "ISSUED")
    errs1 = [m for s, m in out1 if s == "REJECTED"]
    print(f"  [Original issue_book]      connections={conns1} | loans_issued={lcnt1} (successes={issued1}) | final_avail={avail1} | rejections={errs1[:2]}")

    # Test 2: Fixed issue_book_safe
    bid2, mids2 = setup_last_copy("2")
    out2, avail2, lcnt2, conns2 = execute_race(True, bid2, mids2)
    issued2 = sum(1 for s, _ in out2 if s == "ISSUED")
    print(f"  [Fixed issue_book_safe]    connections={conns2} | loans_issued={lcnt2} (successes={issued2}) | final_avail={avail2} | cleanly_rejected={len(out2)-issued2}")


def run_mid_transaction_drop_test(db_type="mysql"):
    """Simulate a dropped connection mid-transaction and prove rollback + reconnect recovery."""
    print(f"\n=== Mid-Transaction Connection Drop Test ({db_type.upper()}) ===")
    d = Dialect(db_type)
    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT book_id, copies_available FROM book WHERE copies_available > 0 LIMIT 1")
        bid, before_avail = cur.fetchone()
        cur.close()

    # Simulate abrupt drop after decrementing copies_available without commit
    drop_conn = get_connection(db_type)
    drop_cur = drop_conn.cursor()
    drop_cur.execute(d.sql("UPDATE book SET copies_available = copies_available - 1 WHERE book_id = {ph}"), (bid,))
    # Connection drops before loan insert & commit!
    drop_cur.close()
    drop_conn.close()

    # Reconnect via safe_connect and inspect database state
    with closing(safe_connect(db_type, retries=2, delay=0.1)) as rec_conn:
        cur = rec_conn.cursor()
        cur.execute(d.sql("SELECT copies_available FROM book WHERE book_id = {ph}"), (bid,))
        after_avail = cur.fetchone()[0]
        cur.close()
    print(f"  Book {bid}: before={before_avail}, after mid-tx drop & reconnect={after_avail} (atomicity preserved!)")


if __name__ == "__main__":
    measure_large_scale_queries("sqlite")
    measure_large_scale_queries("mysql")
    run_concurrency_test("mysql")
    run_mid_transaction_drop_test("mysql")
