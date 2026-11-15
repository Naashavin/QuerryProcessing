import re
import sqlite3
from contextlib import closing
from db_config import get_connection
from dialect import Dialect


def demo_sql_injection_and_quote_failure():
    """Show why f-string / string concatenation fails on O'Brien and allows SQL injection."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE demo_mem (id INTEGER PRIMARY KEY, code TEXT, full_name TEXT)")

    # 1. f-string breaks on apostrophe in "Sneha O'Brien"
    name_with_quote = "Sneha O'Brien"
    bad_sql = f"INSERT INTO demo_mem (code, full_name) VALUES ('M002', '{name_with_quote}')"
    try:
        conn.execute(bad_sql)
    except sqlite3.OperationalError as err:
        print(f"[f-string FAILURE] {type(err).__name__}: {err}")

    # Parameterised query handles apostrophe safely
    conn.execute("INSERT INTO demo_mem (code, full_name) VALUES (?, ?)", ("M002", name_with_quote))
    conn.execute("INSERT INTO demo_mem (code, full_name) VALUES (?, ?)", ("M001", "Arjun Mehta"))
    conn.commit()
    print("[Parameterised OK] Stored:", conn.execute("SELECT code, full_name FROM demo_mem").fetchall())

    # 2. SQL injection payload via string concatenation
    inj_input = "' OR '1'='1"
    vuln_query = f"SELECT code, full_name FROM demo_mem WHERE code = '{inj_input}'"
    leaked = conn.execute(vuln_query).fetchall()
    print(f"[String Concat VULNERABLE] Input={inj_input!r} leaked ALL {len(leaked)} rows: {leaked}")

    safe_res = conn.execute("SELECT code, full_name FROM demo_mem WHERE code = ?", (inj_input,)).fetchall()
    print(f"[Parameterised SAFE]       Input={inj_input!r} treated as literal -> {safe_res}")
    conn.close()


def insert_member(db_type, member_code, full_name, email, joined_on, status="ACTIVE"):
    """Validate in Python, execute parameterised insert, catch IntegrityError cleanly."""
    if not full_name or not full_name.strip():
        return False, "Validation Error: full_name cannot be empty."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or ""):
        return False, f"Validation Error: invalid email format '{email}'."
    if status not in ("ACTIVE", "SUSPENDED", "EXPIRED"):
        return False, f"Validation Error: invalid status '{status}'."

    d = Dialect(db_type)
    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()
        try:
            new_id = d.insert_returning_id(
                cur,
                "INSERT INTO member (member_code, full_name, email, joined_on, status) "
                "VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
                (member_code, full_name.strip(), email.strip().lower(), joined_on, status),
                "member_id",
            )
            conn.commit()
            return True, f"Inserted member_id={new_id} ({member_code})"
        except d.integrity_exceptions() as err:
            conn.rollback()
            return False, f"Database rejected insert ({type(err).__name__}): {err}"
        finally:
            cur.close()


def demo_invalid_inserts(db_type):
    """Attempt 6 invalid inserts on db_type and print exception classes & messages."""
    d = Dialect(db_type)
    print(f"\n=== 6 Invalid Inserts ({db_type.upper()}) ===")
    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT category_id FROM category LIMIT 1")
        cat_id = cur.fetchone()[0]
        cur.execute("SELECT book_id FROM book LIMIT 1")
        book_id = cur.fetchone()[0]

        cases = [
            ("1. Duplicate ISBN", "INSERT INTO book (isbn, title, author, category_id, publication_year, copies_total, copies_available) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})", ("978-0130000001", "Dup Book", "Auth", cat_id, 2020, 2, 2)),
            ("2. Duplicate Email", "INSERT INTO member (member_code, full_name, email, joined_on, status) VALUES ({ph},{ph},{ph},{ph},{ph})", ("M991", "Dup Email", "member001@meridian.edu", "2026-10-01", "ACTIVE")),
            ("3. NULL NOT NULL full_name", "INSERT INTO member (member_code, full_name, email, joined_on, status) VALUES ({ph},{ph},{ph},{ph},{ph})", ("M992", None, "m992@meridian.edu", "2026-10-01", "ACTIVE")),
            ("4. FK Loan unknown member", "INSERT INTO loan (member_id, book_id, issued_on, due_on) VALUES ({ph},{ph},{ph},{ph})", (99999, book_id, "2026-10-01", "2026-10-15")),
            ("5. CHECK negative stock", "INSERT INTO book (isbn, title, author, category_id, publication_year, copies_total, copies_available) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})", ("978-9990000999", "Neg Stock", "Auth", cat_id, 2020, 2, -1)),
            ("6. CHECK invalid status 'VIP'", "INSERT INTO member (member_code, full_name, email, joined_on, status) VALUES ({ph},{ph},{ph},{ph},{ph})", ("M993", "Bad Status", "m993@meridian.edu", "2026-10-01", "VIP")),
        ]
        for label, tmpl, params in cases:
            try:
                cur.execute(d.sql(tmpl), params)
                conn.commit()
                print(f"  [UNEXPECTED PASS] {label}")
            except d.integrity_exceptions() as err:
                conn.rollback()
                print(f"  {label:<32} | {type(err).__name__:<18} | {err}")
        cur.close()


def demo_insert_ignore_and_transactions(db_type):
    d = Dialect(db_type)
    print(f"\n=== Duplicate-Ignore & Transaction Demo ({db_type.upper()}) ===")
    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()

        # 1. Insert-ignore existing category 'Programming'
        ign_sql = d.insert_ignore_sql("category", ["name"], "name")
        cur.execute(ign_sql, ("Programming",))
        conn.commit()
        print(f"  Insert-ignore SQL executed cleanly ({ign_sql}) -> rowcount={cur.rowcount}")

        # 2. Batch of 20 loans where 15th is invalid -> Rollback leaves 0 rows
        cur.execute("SELECT COUNT(*) FROM loan")
        before_cnt = cur.fetchone()[0]
        cur.execute("SELECT member_id FROM member LIMIT 1")
        mid = cur.fetchone()[0]
        cur.execute("SELECT book_id FROM book LIMIT 1")
        bid = cur.fetchone()[0]

        loan_sql = d.sql("INSERT INTO loan (member_id, book_id, issued_on, due_on) VALUES ({ph}, {ph}, {ph}, {ph})")
        try:
            for i in range(1, 21):
                target_mid = 99999 if i == 15 else mid
                cur.execute(loan_sql, (target_mid, bid, "2026-11-01", "2026-11-15"))
            conn.commit()
        except d.integrity_exceptions() as err:
            conn.rollback()
            print(f"  Batch failed at row 15 ({type(err).__name__}) -> Rolled back!")

        cur.execute("SELECT COUNT(*) FROM loan")
        after_rb_cnt = cur.fetchone()[0]
        print(f"  Loan count before={before_cnt}, after rollback={after_rb_cnt} (0 added)")

        # 3. Single valid insert returning generated PK, then clean rollback/cleanup or keep
        new_loan_id = d.insert_returning_id(
            cur,
            "INSERT INTO loan (member_id, book_id, issued_on, due_on) VALUES ({ph}, {ph}, {ph}, {ph})",
            (mid, bid, "2026-11-01", "2026-11-15"),
            "loan_id",
        )
        conn.commit()
        print(f"  Valid single loan committed -> generated primary key loan_id={new_loan_id}")
        # Clean up test row so seeded counts stay crisp
        cur.execute(d.sql("DELETE FROM loan WHERE loan_id = {ph}"), (new_loan_id,))
        conn.commit()
        cur.close()


if __name__ == "__main__":
    print("=== String Formatting Failure & SQL Injection Demo ===")
    demo_sql_injection_and_quote_failure()

    for dbt in ("sqlite", "mysql"):
        demo_invalid_inserts(dbt)
        demo_insert_ignore_and_transactions(dbt)
        ok, msg = insert_member(dbt, "M900", "Test Valid Member", "m900@meridian.edu", "2026-11-01")
        print(f"\n[{dbt.upper()}] insert_member valid test -> {ok}: {msg}")
        ok2, msg2 = insert_member(dbt, "M901", "Dup Email Test", "m900@meridian.edu", "2026-11-01")
        print(f"[{dbt.upper()}] insert_member duplicate test -> {ok2}: {msg2}")
