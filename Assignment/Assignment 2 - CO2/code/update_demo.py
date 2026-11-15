import re
from contextlib import closing
from db_config import get_connection
from dialect import Dialect


def update_member_email(db_type, member_id, new_email):
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", new_email or ""):
        raise ValueError(f"Invalid email format: {new_email}")
    d = Dialect(db_type)
    with closing(get_connection(db_type)) as conn:
        cur = d.cursor(conn, as_dict=True)
        cur.execute(d.sql("SELECT member_id, email FROM member WHERE member_id = {ph}"), (member_id,))
        before = d.fetch_one_dict(cur)

        cur.execute(d.sql("UPDATE member SET email = {ph} WHERE member_id = {ph}"), (new_email, member_id))
        rc = cur.rowcount
        if rc == 0:
            conn.rollback()
            cur.close()
            raise LookupError(f"No member found with member_id={member_id} (rowcount=0)")
        conn.commit()

        cur.execute(d.sql("SELECT member_id, email FROM member WHERE member_id = {ph}"), (member_id,))
        after = d.fetch_one_dict(cur)
        cur.close()
        return before, after, rc


def atomic_return_book(db_type, loan_id, return_date, simulate_failure=False):
    """Atomic two-statement update: update loan.returned_on and increment book.copies_available."""
    d = Dialect(db_type)
    with closing(get_connection(db_type)) as conn:
        cur = d.cursor(conn, as_dict=True)
        cur.execute(d.sql("SELECT loan_id, book_id, returned_on FROM loan WHERE loan_id = {ph}"), (loan_id,))
        loan_row = d.fetch_one_dict(cur)
        if not loan_row or loan_row["returned_on"] is not None:
            cur.close()
            raise ValueError(f"Loan {loan_id} invalid or already returned.")
        book_id = loan_row["book_id"]

        try:
            cur.execute(
                d.sql("UPDATE loan SET returned_on = {ph} WHERE loan_id = {ph} AND returned_on IS NULL"),
                (return_date, loan_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError("Loan update failed.")

            if simulate_failure:
                raise RuntimeError("Simulated power/network failure between loan and book updates!")

            cur.execute(
                d.sql("UPDATE book SET copies_available = copies_available + 1 WHERE book_id = {ph}"),
                (book_id,),
            )
            conn.commit()
            return True, book_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def run_update_demos(db_type):
    d = Dialect(db_type)
    print(f"\n================ UPDATE DEMOS ({db_type.upper()}) ================")

    with closing(get_connection(db_type)) as conn:
        cur = d.cursor(conn, as_dict=True)

        # Find an unreturned loan where book has copies_available < copies_total
        cur.execute(
            "SELECT l.loan_id, l.book_id, l.due_on, l.renew_count, b.copies_available, b.copies_total "
            "FROM loan l JOIN book b ON l.book_id = b.book_id "
            "WHERE l.returned_on IS NULL AND b.copies_available < b.copies_total LIMIT 1"
        )
        target_ret = d.fetch_one_dict(cur)
        ret_loan_id = target_ret["loan_id"]
        ret_book_id = target_ret["book_id"]

        # Find an unreturned loan eligible for renewal (renew_count < 2)
        cur.execute(
            d.sql("SELECT loan_id, due_on, renew_count FROM loan WHERE returned_on IS NULL AND renew_count < 2 AND loan_id != {ph} LIMIT 1"),
            (ret_loan_id,),
        )
        target_ren = d.fetch_one_dict(cur)
        cur.close()

    # Op 1 (Atomic Failure-in-the-middle test first, then real return)
    print(f"\n[Op 1a] Atomic Return Failure-in-Middle (loan_id={ret_loan_id}, book_id={ret_book_id})")
    try:
        atomic_return_book(db_type, ret_loan_id, "2026-11-11", simulate_failure=True)
    except RuntimeError as e:
        print(f"  Caught simulated failure -> {e}")
    with closing(get_connection(db_type)) as conn:
        cur = d.cursor(conn, as_dict=True)
        cur.execute(d.sql("SELECT returned_on FROM loan WHERE loan_id = {ph}"), (ret_loan_id,))
        r_chk = d.fetch_one_dict(cur)
        cur.execute(d.sql("SELECT copies_available FROM book WHERE book_id = {ph}"), (ret_book_id,))
        b_chk = d.fetch_one_dict(cur)
        print(f"  After ROLLBACK: loan.returned_on={r_chk['returned_on']}, book.copies_available={b_chk['copies_available']} (unchanged!)")
        cur.close()

    print(f"[Op 1b] Atomic Return Success (loan_id={ret_loan_id})")
    atomic_return_book(db_type, ret_loan_id, "2026-11-11", simulate_failure=False)
    with closing(get_connection(db_type)) as conn:
        cur = d.cursor(conn, as_dict=True)
        cur.execute(d.sql("SELECT returned_on FROM loan WHERE loan_id = {ph}"), (ret_loan_id,))
        r_after = d.fetch_one_dict(cur)
        cur.execute(d.sql("SELECT copies_available FROM book WHERE book_id = {ph}"), (ret_book_id,))
        b_after = d.fetch_one_dict(cur)
        print(f"  After COMMIT: loan.returned_on={r_after['returned_on']}, book.copies_available={b_after['copies_available']}")

        # Op 2: Renew loan (+7 days if renew_count < 2)
        ren_id = target_ren["loan_id"]
        new_due_sql = d.add_days_expr("due_on", 7)
        cur.execute(
            d.sql(f"UPDATE loan SET due_on = {new_due_sql}, renew_count = renew_count + 1 WHERE loan_id = {{ph}} AND renew_count < 2"),
            (ren_id,),
        )
        ren_rc = cur.rowcount
        conn.commit()
        cur.execute(d.sql("SELECT loan_id, due_on, renew_count FROM loan WHERE loan_id = {ph}"), (ren_id,))
        ren_after = d.fetch_one_dict(cur)
        print(f"\n[Op 2] Renew Loan (loan_id={ren_id}): before=({target_ren['due_on']}, renew={target_ren['renew_count']}) -> after=({ren_after['due_on']}, renew={ren_after['renew_count']}), rowcount={ren_rc}")

        # Op 4: Bulk expire members joined before 2024-03-01
        cur.execute("SELECT COUNT(*) AS cnt FROM member WHERE joined_on < '2024-03-01' AND status = 'ACTIVE'")
        before_exp = d.fetch_one_dict(cur)["cnt"]
        cur.execute("UPDATE member SET status = 'EXPIRED' WHERE joined_on < '2024-03-01' AND status = 'ACTIVE'")
        bulk_rc = cur.rowcount
        conn.commit()
        print(f"[Op 4] Bulk Expire Members (joined < 2024-03-01): eligible_before={before_exp}, rowcount={bulk_rc}")

        # Op 5: Record fine payment
        cur.execute(d.sql("SELECT fine_id, amount, paid FROM fine WHERE paid = {ph} LIMIT 1"), (d.bool_val(False),))
        f_before = d.fetch_one_dict(cur)
        cur.execute(d.sql("UPDATE fine SET paid = {ph} WHERE fine_id = {ph}"), (d.bool_val(True), f_before["fine_id"]))
        f_rc = cur.rowcount
        conn.commit()
        cur.execute(d.sql("SELECT fine_id, amount, paid FROM fine WHERE fine_id = {ph}"), (f_before["fine_id"],))
        f_after = d.fetch_one_dict(cur)
        print(f"[Op 5] Record Fine Payment: before={f_before} -> after={f_after}, rowcount={f_rc}")

        # Op 6: Adjust book stock (+1 total & available)
        cur.execute("SELECT book_id, copies_total, copies_available FROM book WHERE book_id = 1")
        stk_before = d.fetch_one_dict(cur)
        cur.execute("UPDATE book SET copies_total = copies_total + 1, copies_available = copies_available + 1 WHERE book_id = 1")
        stk_rc = cur.rowcount
        conn.commit()
        cur.execute("SELECT book_id, copies_total, copies_available FROM book WHERE book_id = 1")
        stk_after = d.fetch_one_dict(cur)
        print(f"[Op 6] Adjust Stock: before={stk_before} -> after={stk_after}, rowcount={stk_rc}")

        # Same-Value Update Rowcount Experiment
        cur.execute("SELECT member_id, status FROM member WHERE status = 'ACTIVE' LIMIT 1")
        sv_mem = d.fetch_one_dict(cur)
        cur.execute(d.sql("UPDATE member SET status = {ph} WHERE member_id = {ph}"), (sv_mem["status"], sv_mem["member_id"]))
        same_rc = cur.rowcount
        conn.commit()
        print(f"[Same-Value Rowcount] Updated member_id={sv_mem['member_id']} status to existing '{sv_mem['status']}' -> rowcount={same_rc}")

        # Missing-WHERE Clause Danger Demonstration (on temp copy table, rolled back)
        cur.execute("DROP TABLE IF EXISTS _member_copy")
        cur.execute("CREATE TABLE _member_copy AS SELECT member_id, status FROM member")
        conn.commit()
        cur.execute("UPDATE _member_copy SET status = 'SUSPENDED'")  # NO WHERE CLAUSE!
        bad_rc = cur.rowcount
        conn.rollback()
        cur.execute("SELECT COUNT(*) AS cnt FROM _member_copy WHERE status = 'ACTIVE'")
        restored_active = d.fetch_one_dict(cur)["cnt"]
        cur.execute("DROP TABLE IF EXISTS _member_copy")
        conn.commit()
        print(f"[Missing-WHERE Demo] UPDATE without WHERE hit {bad_rc} rows -> ROLLBACK restored {restored_active} ACTIVE rows!")
        cur.close()

    # Op 3: update_member_email (valid & nonexistent error check)
    bef, aft, rc = update_member_email(db_type, 1, "arjun.updated@meridian.edu")
    print(f"[Op 3a] Update Member Email: before={bef} -> after={aft}, rowcount={rc}")
    try:
        update_member_email(db_type, 99999, "nobody@meridian.edu")
    except LookupError as err:
        print(f"[Op 3b] Zero-match guard caught -> {err}")


if __name__ == "__main__":
    for dbt in ("sqlite", "mysql"):
        run_update_demos(dbt)
