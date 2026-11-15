import json
import sqlite3
from contextlib import closing
from db_config import get_connection
from dialect import Dialect


def safe_delete_member(db_type, member_id, simulate_error=False):
    """Single-transaction safe deletion: check BR9, archive to audit_log, delete member, rollback on error."""
    d = Dialect(db_type)
    with closing(get_connection(db_type)) as conn:
        cur = d.cursor(conn, as_dict=True)
        try:
            cur.execute(d.sql("SELECT * FROM member WHERE member_id = {ph}"), (member_id,))
            mem = d.fetch_one_dict(cur)
            if not mem:
                raise LookupError(f"Member {member_id} does not exist.")

            # BR9 check 1: unreturned loans
            cur.execute(
                d.sql("SELECT COUNT(*) AS cnt FROM loan WHERE member_id = {ph} AND returned_on IS NULL"),
                (member_id,),
            )
            active_loans = d.fetch_one_dict(cur)["cnt"]
            if active_loans > 0:
                raise PermissionError(f"Refused (BR9): Member {member_id} has {active_loans} unreturned loan(s).")

            # BR9 check 2: unpaid fines
            cur.execute(
                d.sql(
                    "SELECT COUNT(*) AS cnt FROM fine f JOIN loan l ON f.loan_id = l.loan_id "
                    "WHERE l.member_id = {ph} AND f.paid = {ph}"
                ),
                (member_id, d.bool_val(False)),
            )
            unpaid_fines = d.fetch_one_dict(cur)["cnt"]
            if unpaid_fines > 0:
                raise PermissionError(f"Refused (BR9): Member {member_id} has {unpaid_fines} unpaid fine(s).")

            # Step 1: Write member record snapshot to audit_log (BR10)
            mem_serializable = {k: str(v) for k, v in mem.items()}
            cur.execute(
                d.sql("INSERT INTO audit_log (table_name, record_key, action, details) VALUES ({ph}, {ph}, {ph}, {ph})"),
                ("member", str(member_id), "HARD_DELETE", json.dumps(mem_serializable)),
            )

            if simulate_error:
                raise RuntimeError("Simulated mid-transaction crash after audit insert!")

            # Step 2: Delete member
            cur.execute(d.sql("DELETE FROM member WHERE member_id = {ph}"), (member_id,))
            conn.commit()
            return True, f"Member {member_id} ({mem['member_code']}) archived in audit_log and deleted."
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def soft_delete_member(db_type, member_id):
    """Soft delete alternative: mark status='DELETED' and log to audit_log without breaking history."""
    d = Dialect(db_type)
    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()
        cur.execute(d.sql("UPDATE member SET status = 'DELETED' WHERE member_id = {ph}"), (member_id,))
        rc = cur.rowcount
        cur.execute(
            d.sql("INSERT INTO audit_log (table_name, record_key, action, details) VALUES ({ph}, {ph}, {ph}, {ph})"),
            ("member", str(member_id), "SOFT_DELETE", "Status updated to DELETED; loan history retained."),
        )
        conn.commit()
        cur.close()
        return rc


def test_fk_policies(db_type):
    """Test RESTRICT, CASCADE, and SET NULL policies directly on db_type."""
    d = Dialect(db_type)
    results = {}
    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()
        for policy in ("RESTRICT", "CASCADE", "SET NULL"):
            cur.execute("DROP TABLE IF EXISTS _fk_child")
            cur.execute("DROP TABLE IF EXISTS _fk_parent")
            cur.execute("CREATE TABLE _fk_parent (id INT PRIMARY KEY)")
            cur.execute(
                f"CREATE TABLE _fk_child (cid INT PRIMARY KEY, pid INT NULL, "
                f"FOREIGN KEY (pid) REFERENCES _fk_parent(id) ON DELETE {policy})"
            )
            cur.execute("INSERT INTO _fk_parent VALUES (1)")
            cur.execute("INSERT INTO _fk_child VALUES (10, 1)")
            conn.commit()
            try:
                cur.execute("DELETE FROM _fk_parent WHERE id = 1")
                conn.commit()
                cur.execute("SELECT cid, pid FROM _fk_child")
                remaining = cur.fetchall()
                results[policy] = f"Allowed -> child rows={remaining}"
            except d.integrity_exceptions() as err:
                conn.rollback()
                results[policy] = f"Blocked ({type(err).__name__})"
        cur.execute("DROP TABLE IF EXISTS _fk_child")
        cur.execute("DROP TABLE IF EXISTS _fk_parent")
        conn.commit()
        cur.close()
    return results


def run_delete_demos(db_type):
    d = Dialect(db_type)
    print(f"\n================ DELETE DEMOS ({db_type.upper()}) ================")

    # 1. Referential Integrity check: delete member 1 who has loans
    if db_type == "sqlite":
        # Briefly test with PRAGMA foreign_keys = OFF on a temp copy or check behavior
        c_off = sqlite3.connect(":memory:")
        c_off.execute("PRAGMA foreign_keys = OFF;")
        c_off.execute("CREATE TABLE p(id INT PRIMARY KEY);")
        c_off.execute("CREATE TABLE c(cid INT, pid INT REFERENCES p(id) ON DELETE RESTRICT);")
        c_off.executescript("INSERT INTO p VALUES (1); INSERT INTO c VALUES (10, 1);")
        c_off.execute("DELETE FROM p WHERE id = 1;")
        orphan_cnt = c_off.execute("SELECT COUNT(*) FROM c").fetchone()[0]
        c_off.close()
        print(f"  [SQLite FK=OFF] Parent delete SUCCEEDED silently -> {orphan_cnt} orphan child left!")

    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM member WHERE member_id = 1")
            conn.commit()
            print("  [FK=ON] Unexpected delete success")
        except d.integrity_exceptions() as err:
            conn.rollback()
            print(f"  [{db_type.upper()} FK=ON] Delete member 1 BLOCKED -> {type(err).__name__}: {str(err)[:85]}")
        cur.close()

    # 2. Foreign key policy matrix
    print("  [FK Policy Tests]", test_fk_policies(db_type))

    # 3. 4 Conditional DELETE operations
    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()
        # Del 1: Delete paid fines
        cur.execute(d.sql("DELETE FROM fine WHERE paid = {ph}"), (d.bool_val(True),))
        print(f"  [Cond Delete 1] Paid fines deleted: rowcount={cur.rowcount}")

        # Del 2: Delete old returned loans (without unpaid fines) older than 2026-10-10
        cur.execute(
            "DELETE FROM loan WHERE returned_on IS NOT NULL AND returned_on < '2026-10-10' "
            "AND loan_id NOT IN (SELECT loan_id FROM fine)"
        )
        print(f"  [Cond Delete 2] Returned loans < 2026-10-10 deleted: rowcount={cur.rowcount}")

        # Del 3: Delete never-borrowed book #60
        cur.execute("DELETE FROM book WHERE book_id = 60 AND book_id NOT IN (SELECT book_id FROM loan)")
        print(f"  [Cond Delete 3] Unborrowed book #60 deleted: rowcount={cur.rowcount}")

        # Del 4: Delete temporary/unused suspended member #26 (no loans)
        cur.execute("DELETE FROM member WHERE member_id = 26 AND status = 'SUSPENDED' AND member_id NOT IN (SELECT member_id FROM loan)")
        print(f"  [Cond Delete 4] Suspended loan-free member #26 deleted: rowcount={cur.rowcount}")
        conn.commit()
        cur.close()

    # 4. Safe Delete Member demonstrations (Refusal, Rollback, Success)
    try:
        safe_delete_member(db_type, 1)
    except PermissionError as e:
        print(f"  [safe_delete_member Refusal]  -> {e}")

    try:
        safe_delete_member(db_type, 30, simulate_error=True)
    except RuntimeError as e:
        print(f"  [safe_delete_member Rollback] -> Caught {e}; member 30 & audit_log untouched!")

    ok, msg = safe_delete_member(db_type, 30, simulate_error=False)
    print(f"  [safe_delete_member Success]  -> {msg}")

    # Soft delete demonstration on member 2 (who has loans)
    rc_soft = soft_delete_member(db_type, 2)
    print(f"  [soft_delete_member] Member 2 marked DELETED (rowcount={rc_soft}); loan history intact.")

    with closing(get_connection(db_type)) as conn:
        cur = d.cursor(conn, as_dict=True)
        cur.execute("SELECT log_id, table_name, record_key, action FROM audit_log ORDER BY log_id")
        print("  [audit_log contents]:", d.fetch_dicts(cur))
        cur.close()


if __name__ == "__main__":
    for dbt in ("sqlite", "mysql"):
        run_delete_demos(dbt)
