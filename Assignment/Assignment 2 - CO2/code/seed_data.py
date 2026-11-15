import random
import sys
from contextlib import closing
from datetime import date, timedelta
from create_schema import execute_schema
from db_config import get_connection
from dialect import Dialect


CATEGORIES = [
    "Programming",
    "Algorithms",
    "Databases",
    "Web",
    "Mathematics",
    "Fiction",
]

SAMPLE_TITLES = [
    "Clean Code", "Design Patterns", "Introduction to Algorithms", "Database System Concepts",
    "Fluent Python", "Effective Java", "Designing Data-Intensive Applications", "Computer Networks",
    "Discrete Mathematics", "Linear Algebra Done Right", "Learning SQL", "PostgreSQL Up and Running",
    "JavaScript: The Good Parts", "HTML & CSS Guide", "Operating System Concepts", "Compiler Construction",
    "Deep Learning Basics", "Data Wrangling with Python", "Foundations of Cryptography", "The Pragmatic Programmer",
]

FIRST_NAMES = ["Arjun", "Sneha", "Karthik", "Divya", "Neha", "Imran", "Priya", "Rohan", "Kavitha", "Vikram", "Ananya", "Suresh"]
LAST_NAMES = ["Mehta", "O'Brien", "Nair", "Sharma", "Khan", "Reddy", "Menon", "Verma", "Rao", "Das", "Iyer", "Patel"]


def seed_database(db_type, seed=42):
    rng = random.Random(seed)
    d = Dialect(db_type)
    execute_schema(db_type)

    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()

        # 1. Single inserts for 6 categories using execute()
        cat_ids = []
        for cname in CATEGORIES:
            cid = d.insert_returning_id(
                cur,
                "INSERT INTO category (name) VALUES ({ph})",
                (cname,),
                "category_id",
            )
            cat_ids.append(cid)

        # 2. Bulk insert 60 books using executemany()
        books_rows = []
        for i in range(1, 61):
            isbn = f"978-013{i:07d}"
            base_title = SAMPLE_TITLES[(i - 1) % len(SAMPLE_TITLES)]
            title = f"{base_title} (Vol {((i - 1) // len(SAMPLE_TITLES)) + 1})" if i > len(SAMPLE_TITLES) else base_title
            author = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
            cid = cat_ids[(i - 1) % len(cat_ids)]
            year = rng.randint(1998, 2025)
            total = 1 if i % 10 == 0 else rng.randint(2, 6)
            # Keep last 5 books completely available and unborrowed for LEFT JOIN queries
            avail = total if i > 55 else (0 if i % 15 == 0 else rng.randint(1, total))
            books_rows.append((isbn, title, author, cid, year, total, avail))

        cur.executemany(
            d.sql(
                "INSERT INTO book (isbn, title, author, category_id, publication_year, copies_total, copies_available) "
                "VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})"
            ),
            books_rows,
        )

        # 3. Bulk insert 30 members using executemany()
        members_rows = []
        base_join = date(2024, 1, 10)
        for i in range(1, 31):
            code = f"M{i:03d}"
            fname = "Sneha O'Brien" if i == 2 else f"{FIRST_NAMES[(i - 1) % len(FIRST_NAMES)]} {LAST_NAMES[(i * 3) % len(LAST_NAMES)]}"
            email = f"member{i:03d}@meridian.edu"
            joined = (base_join + timedelta(days=i * 15)).isoformat()
            if i in (25, 26):
                status = "SUSPENDED"
            elif i in (27, 28):
                status = "EXPIRED"
            else:
                status = "ACTIVE"
            members_rows.append((code, fname, email, joined, status))

        cur.executemany(
            d.sql(
                "INSERT INTO member (member_code, full_name, email, joined_on, status) "
                "VALUES ({ph}, {ph}, {ph}, {ph}, {ph})"
            ),
            members_rows,
        )

        # Retrieve actual generated book_id and member_id lists
        cur.execute("SELECT book_id FROM book ORDER BY book_id")
        book_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT member_id FROM member ORDER BY member_id")
        member_ids = [r[0] for r in cur.fetchall()]

        # 4. Bulk insert 80 loans using executemany() (only use first 55 books so books 56-60 remain unborrowed)
        loans_rows = []
        ref_today = date(2026, 11, 11)
        for i in range(1, 81):
            mid = member_ids[(i - 1) % 24]  # keep members 25-30 loan-free for safe-delete / status tests
            bid = book_ids[(i - 1) % 55]
            issued = ref_today - timedelta(days=rng.randint(5, 60))
            due = issued + timedelta(days=14)
            if i <= 50:
                # Returned loans (15 of them returned late so fines can be assessed)
                delay = rng.randint(2, 10) if i <= 15 else rng.randint(-5, 0)
                ret = (due + timedelta(days=delay)).isoformat()
                renews = rng.randint(0, 1)
            else:
                # Active unreturned loans (including overdue ones where due < ref_today)
                ret = None
                renews = rng.randint(0, 2)
            loans_rows.append((mid, bid, issued.isoformat(), due.isoformat(), ret, renews))

        cur.executemany(
            d.sql(
                "INSERT INTO loan (member_id, book_id, issued_on, due_on, returned_on, renew_count) "
                "VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})"
            ),
            loans_rows,
        )

        # 5. Insert 12 fines on the late-returned loans
        cur.execute("SELECT loan_id, due_on, returned_on FROM loan WHERE returned_on IS NOT NULL AND returned_on > due_on ORDER BY loan_id")
        late_loans = cur.fetchall()
        fines_rows = []
        for idx, (lid, due_val, ret_val) in enumerate(late_loans[:12]):
            due_d = due_val if isinstance(due_val, date) else date.fromisoformat(str(due_val))
            ret_d = ret_val if isinstance(ret_val, date) else date.fromisoformat(str(ret_val))
            overdue_days = (ret_d - due_d).days
            amt = round(overdue_days * 2.0, 2)
            paid_flag = d.bool_val(idx % 3 == 0)
            fines_rows.append((lid, amt, ret_d.isoformat(), paid_flag))

        cur.executemany(
            d.sql("INSERT INTO fine (loan_id, amount, assessed_on, paid) VALUES ({ph}, {ph}, {ph}, {ph})"),
            fines_rows,
        )

        conn.commit()

        # Verify counts with SQL COUNT(*)
        print(f"=== Seeded {db_type.upper()} Row Counts ===")
        for tbl in ("category", "book", "member", "loan", "fine"):
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            print(f"  {tbl:<10}: {cur.fetchone()[0]} rows")
        cur.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        seed_database(sys.argv[1])
    else:
        for dbt in ("sqlite", "mysql"):
            seed_database(dbt)

