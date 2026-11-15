import argparse
from contextlib import closing
from pathlib import Path
from db_config import BASE_DIR, get_connection
from dialect import Dialect
from repositories import BookRepository, LoanRepository, MemberRepository


def ddl_in_transaction_experiment(db_type):
    """Test whether DDL (CREATE TABLE) rolls back inside an explicit transaction on db_type."""
    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS _ddl_tx_test")
        conn.commit()

        try:
            Dialect(db_type).begin_tx(cur)
            cur.execute("CREATE TABLE _ddl_tx_test (id INT PRIMARY KEY)")
            conn.rollback()
        except Exception:
            conn.rollback()

        exists = False
        try:
            cur.execute("SELECT COUNT(*) FROM _ddl_tx_test")
            cur.fetchone()
            exists = True
        except Exception:
            conn.rollback()
            exists = False

        if exists:
            cur.execute("DROP TABLE IF EXISTS _ddl_tx_test")
            conn.commit()
        cur.close()
        print(f"[{db_type.upper()}] DDL inside explicit transaction -> After ROLLBACK, table still exists? {exists}")


def separation_check():
    """Verify zero database-type conditional branches exist inside repositories.py or meridianlib.py."""
    import re
    for fname in ("repositories.py", "meridianlib.py"):
        text = (BASE_DIR / fname).read_text(encoding="utf-8")
        # Look for conditional branching on db_type / args.db outside Dialect/db_config
        matches = re.findall(r"^\s*(?:if|elif)\s+.*\b(?:db_type|args\.db)\b\s*==", text, flags=re.MULTILINE)
        print(f"Separation Check ({fname:<15}): {len(matches)} DB-type conditional branches found.")


def main():
    parser = argparse.ArgumentParser(description="MeridianLib Multi-Database CLI Application")
    parser.add_argument("--db", required=True, choices=["sqlite", "mysql", "postgres"], help="Target database backend")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_am = sub.add_parser("add-member")
    p_am.add_argument("--code", required=True)
    p_am.add_argument("--name", required=True)
    p_am.add_argument("--email", required=True)
    p_am.add_argument("--joined", default="2026-11-11")

    p_ab = sub.add_parser("add-book")
    p_ab.add_argument("--isbn", required=True)
    p_ab.add_argument("--title", required=True)
    p_ab.add_argument("--author", required=True)
    p_ab.add_argument("--category-id", type=int, default=1)
    p_ab.add_argument("--year", type=int, default=2024)
    p_ab.add_argument("--copies", type=int, default=3)

    p_sb = sub.add_parser("search-books")
    p_sb.add_argument("--q", required=True)

    p_ib = sub.add_parser("issue-book")
    p_ib.add_argument("--member-id", type=int, required=True)
    p_ib.add_argument("--book-id", type=int, required=True)

    p_rb = sub.add_parser("return-book")
    p_rb.add_argument("--loan-id", type=int, required=True)
    p_rb.add_argument("--date", default="2026-11-11")

    p_rl = sub.add_parser("renew-loan")
    p_rl.add_argument("--loan-id", type=int, required=True)

    p_dm = sub.add_parser("safe-delete-member")
    p_dm.add_argument("--member-id", type=int, required=True)

    sub.add_parser("overdue-report")
    sub.add_parser("ddl-tx-demo")
    sub.add_parser("separation-check")

    args = parser.parse_args()
    if args.cmd == "ddl-tx-demo":
        ddl_in_transaction_experiment(args.db)
        return
    if args.cmd == "separation-check":
        separation_check()
        return

    dialect = Dialect(args.db)
    with closing(get_connection(args.db)) as conn:
        members = MemberRepository(conn, dialect)
        books = BookRepository(conn, dialect)
        loans = LoanRepository(conn, dialect)

        if args.cmd == "add-member":
            mid = members.add(args.code, args.name, args.email, args.joined)
            print(f"[{args.db}] Added member_id={mid}")
        elif args.cmd == "add-book":
            bid = books.add(args.isbn, args.title, args.author, args.category_id, args.year, args.copies)
            print(f"[{args.db}] Added book_id={bid}")
        elif args.cmd == "search-books":
            rows = books.search(args.q)
            print(f"[{args.db}] Found {len(rows)} matching book(s):", rows[:3])
        elif args.cmd == "issue-book":
            lid = loans.issue_book_safe(args.member_id, args.book_id)
            print(f"[{args.db}] Issued loan_id={lid}")
        elif args.cmd == "return-book":
            fine = loans.return_book(args.loan_id, args.date)
            print(f"[{args.db}] Returned loan_id={args.loan_id}, fine_assessed=Rs.{fine:.2f}")
        elif args.cmd == "renew-loan":
            loans.renew_loan(args.loan_id)
            print(f"[{args.db}] Renewed loan_id={args.loan_id} (+7 days)")
        elif args.cmd == "safe-delete-member":
            members.safe_delete(args.member_id)
            print(f"[{args.db}] Safely deleted member_id={args.member_id}")
        elif args.cmd == "overdue-report":
            rows = loans.overdue_report()
            print(f"[{args.db}] Overdue unreturned loans count={len(rows)} (top 3: {rows[:3]})")


if __name__ == "__main__":
    main()
