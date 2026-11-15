from contextlib import closing
from db_config import get_connection
from dialect import Dialect


def build_queries(db_type):
    d = Dialect(db_type)
    today = d.today_expr()
    paid_false = d.bool_val(False)

    return [
        (
            "Q1: Books in 'Programming' ordered by title",
            d.sql(
                "SELECT b.book_id, b.isbn, b.title, b.copies_available "
                "FROM book b JOIN category c ON b.category_id = c.category_id "
                "WHERE c.name = {ph} ORDER BY b.title"
            ),
            ("Programming",),
            "fetchall",
        ),
        (
            "Q2: Member counts grouped by status",
            "SELECT status, COUNT(*) AS member_count FROM member GROUP BY status ORDER BY status",
            (),
            "fetchall",
        ),
        (
            "Q3: Books with fewer than 2 copies available",
            "SELECT book_id, title, copies_total, copies_available FROM book WHERE copies_available < 2 ORDER BY book_id",
            (),
            "fetchmany",
        ),
        (
            "Q4: Overdue unreturned loans",
            f"SELECT l.loan_id, m.member_code, m.full_name, b.title, l.due_on "
            f"FROM loan l JOIN member m ON l.member_id = m.member_id "
            f"JOIN book b ON l.book_id = b.book_id "
            f"WHERE l.returned_on IS NULL AND l.due_on < {today} ORDER BY l.due_on",
            (),
            "iter",
        ),
        (
            "Q5: Members with >= 3 total loans (GROUP BY + HAVING)",
            "SELECT m.member_code, m.full_name, COUNT(l.loan_id) AS total_loans "
            "FROM member m JOIN loan l ON m.member_id = l.member_id "
            "GROUP BY m.member_id, m.member_code, m.full_name "
            "HAVING COUNT(l.loan_id) >= 3 ORDER BY total_loans DESC, m.member_code",
            (),
            "fetchall",
        ),
        (
            "Q6: Top 5 most borrowed books",
            "SELECT b.book_id, b.title, COUNT(l.loan_id) AS times_borrowed "
            "FROM book b JOIN loan l ON b.book_id = l.book_id "
            "GROUP BY b.book_id, b.title ORDER BY times_borrowed DESC, b.book_id LIMIT 5",
            (),
            "fetchall",
        ),
        (
            "Q7: Total unpaid fines per member",
            d.sql(
                "SELECT m.member_code, m.full_name, SUM(f.amount) AS total_unpaid "
                "FROM fine f JOIN loan l ON f.loan_id = l.loan_id "
                "JOIN member m ON l.member_id = m.member_id "
                "WHERE f.paid = {ph} "
                "GROUP BY m.member_id, m.member_code, m.full_name ORDER BY total_unpaid DESC, m.member_code"
            ),
            (paid_false,),
            "fetchall",
        ),
        (
            "Q8: Case-insensitive LIKE title search ('python')",
            f"SELECT book_id, title, author FROM book WHERE {d.ilike('title')} ORDER BY book_id",
            ("%python%",),
            "fetchall",
        ),
        (
            "Q9: Books never borrowed (LEFT JOIN)",
            "SELECT b.book_id, b.isbn, b.title "
            "FROM book b LEFT JOIN loan l ON b.book_id = l.book_id "
            "WHERE l.loan_id IS NULL ORDER BY b.book_id",
            (),
            "fetchall",
        ),
        (
            "Q10: Single book lookup by user-supplied ISBN (fetchone)",
            d.sql("SELECT book_id, isbn, title, copies_total, copies_available FROM book WHERE isbn = {ph}"),
            ("978-0130000001",),
            "fetchone",
        ),
    ]


def print_table(title, rows):
    print(f"\n--- {title} (rows={len(rows)}) ---")
    if not rows:
        print("  (No rows returned)")
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(c), max(len(str(r[c])) for r in rows)) for c in cols}
    widths = {c: min(w, 34) for c, w in widths.items()}
    header = " | ".join(f"{c:<{widths[c]}}" for c in cols)
    print("  " + header)
    print("  " + "-" * len(header))
    for r in rows:
        line = " | ".join(f"{str(r[c])[:widths[c]]:<{widths[c]}}" for c in cols)
        print("  " + line)


def run_all_queries(db_type, show_output=True):
    d = Dialect(db_type)
    results = {}
    with closing(get_connection(db_type)) as conn:
        for title, sql, params, fetch_mode in build_queries(db_type):
            cur = d.cursor(conn, as_dict=True)
            cur.execute(sql, params)
            if fetch_mode == "fetchone":
                row = d.fetch_one_dict(cur)
                rows = [row] if row is not None else []
            elif fetch_mode == "fetchmany":
                rows = []
                while True:
                    batch = cur.fetchmany(5)
                    if not batch:
                        break
                    rows.extend(dict(r) for r in batch)
            elif fetch_mode == "iter":
                rows = [dict(r) for r in cur]
            else:
                rows = d.fetch_dicts(cur)
            cur.close()
            results[title] = rows
            if show_output:
                print_table(f"[{db_type.upper()}] {title}", rows[:6])
    return results


if __name__ == "__main__":
    for dbt in ("sqlite", "mysql"):
        run_all_queries(dbt, show_output=True)

