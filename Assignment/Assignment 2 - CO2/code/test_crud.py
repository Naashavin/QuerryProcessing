import sqlite3
import unittest
from contextlib import closing
from create_schema import execute_schema
from db_config import get_connection
from delete_demo import safe_delete_member
from dialect import Dialect
from repositories import BookRepository, LoanRepository, MemberRepository
from safe_connect import is_transient_error, safe_connect
from seed_data import seed_database


def is_backend_available(db_type):
    if db_type == "sqlite":
        return True
    try:
        with closing(get_connection(db_type)):
            return True
    except Exception:
        return False


class BaseMeridianCRUDTests:
    DB_TYPE = None

    @classmethod
    def setUpClass(cls):
        if not is_backend_available(cls.DB_TYPE):
            raise unittest.SkipTest(f"{cls.DB_TYPE} server not reachable in local environment.")
        seed_database(cls.DB_TYPE, seed=42)

    def setUp(self):
        self.d = Dialect(self.DB_TYPE)
        self.conn = get_connection(self.DB_TYPE)
        self.members = MemberRepository(self.conn, self.d)
        self.books = BookRepository(self.conn, self.d)
        self.loans = LoanRepository(self.conn, self.d)

    def tearDown(self):
        self.conn.close()

    def test_01_create_member_valid(self):
        mid = self.members.add("MT01", "Test Member 01", "mt01@meridian.edu", "2026-11-01")
        self.assertGreater(mid, 0)

    def test_02_create_member_apostrophe_safe(self):
        mid = self.members.add("MT02", "Liam O'Connor", "liam.oc@meridian.edu", "2026-11-01")
        row = self.members.get_by_id(mid)
        self.assertEqual(row["full_name"], "Liam O'Connor")

    def test_03_create_member_duplicate_email_rejected(self):
        with self.assertRaises(self.d.integrity_exceptions()):
            self.members.add("MT03", "Dup Email", "member001@meridian.edu", "2026-11-01")

    def test_04_create_member_null_name_rejected(self):
        cur = self.conn.cursor()
        with self.assertRaises(self.d.integrity_exceptions()):
            cur.execute(
                self.d.sql("INSERT INTO member (member_code, full_name, email, joined_on) VALUES ({ph},{ph},{ph},{ph})"),
                ("MT04", None, "mt04@meridian.edu", "2026-11-01"),
            )
            self.conn.commit()
        self.conn.rollback()
        cur.close()

    def test_05_create_member_invalid_status_check(self):
        with self.assertRaises(self.d.integrity_exceptions()):
            self.members.add("MT05", "Bad Status", "mt05@meridian.edu", "2026-11-01", status="VIP")

    def test_06_create_book_valid(self):
        bid = self.books.add("978-8880000001", "SQL Internals", "J. Doe", 1, 2023, 4)
        self.assertGreater(bid, 0)

    def test_07_create_book_duplicate_isbn_rejected(self):
        with self.assertRaises(self.d.integrity_exceptions()):
            self.books.add("978-0130000001", "Dup ISBN Book", "A. B", 1, 2020, 2)

    def test_08_create_book_negative_available_check(self):
        cur = self.conn.cursor()
        with self.assertRaises(self.d.integrity_exceptions()):
            cur.execute(
                self.d.sql("INSERT INTO book (isbn, title, author, category_id, publication_year, copies_total, copies_available) VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})"),
                ("978-8880000002", "Neg Copies", "Auth", 1, 2020, 2, -1),
            )
            self.conn.commit()
        self.conn.rollback()
        cur.close()

    def test_09_read_search_books_case_insensitive(self):
        rows = self.books.search("python")
        self.assertGreaterEqual(len(rows), 1)

    def test_10_read_sql_injection_blocked(self):
        rows = self.books.search("' OR '1'='1")
        self.assertEqual(len(rows), 0)

    def test_11_read_overdue_report(self):
        rows = self.loans.overdue_report()
        self.assertGreater(len(rows), 0)

    def test_12_issue_book_valid_decrements_stock(self):
        bid = self.books.add("978-8880000003", "Issue Target Book", "Author X", 1, 2024, 2)
        mid = self.members.add("MT12", "Issue Member", "mt12@meridian.edu", "2026-11-01")
        lid = self.loans.issue_book_safe(mid, bid, "2026-11-01")
        self.assertGreater(lid, 0)
        cur = self.d.cursor(self.conn, as_dict=True)
        cur.execute(self.d.sql("SELECT copies_available FROM book WHERE book_id = {ph}"), (bid,))
        self.assertEqual(self.d.fetch_one_dict(cur)["copies_available"], 1)
        cur.close()

    def test_13_issue_book_unknown_member_fk_rejected(self):
        with self.assertRaises(self.d.integrity_exceptions()):
            self.loans.issue_book_safe(99999, 1, "2026-11-01")

    def test_14_issue_book_br7_max_3_active_loans(self):
        mid = self.members.add("MT14", "Limit Member", "mt14@meridian.edu", "2026-11-01")
        for idx in range(3):
            bid = self.books.add(f"978-888000010{idx}", f"Limit Book {idx}", "Auth", 1, 2024, 2)
            self.loans.issue_book_safe(mid, bid, "2026-11-01")
        bid4 = self.books.add("978-8880000109", "Limit Book 4", "Auth", 1, 2024, 2)
        with self.assertRaises(ValueError):
            self.loans.issue_book_safe(mid, bid4, "2026-11-01")

    def test_15_return_book_on_time_zero_fine(self):
        bid = self.books.add("978-8880000015", "OnTime Book", "Auth", 1, 2024, 1)
        mid = self.members.add("MT15", "OnTime Member", "mt15@meridian.edu", "2026-11-01")
        lid = self.loans.issue_book_safe(mid, bid, "2026-11-01")
        fine = self.loans.return_book(lid, "2026-11-10")
        self.assertEqual(fine, 0.0)

    def test_16_return_book_late_assesses_fine_br8(self):
        bid = self.books.add("978-8880000016", "Late Book", "Auth", 1, 2024, 1)
        mid = self.members.add("MT16", "Late Member", "mt16@meridian.edu", "2026-10-01")
        lid = self.loans.issue_book_safe(mid, bid, "2026-10-01")  # due 2026-10-15
        fine = self.loans.return_book(lid, "2026-10-20")  # 5 days * Rs.2 = Rs.10
        self.assertEqual(fine, 10.0)

    def test_17_renew_loan_br11_max_twice(self):
        bid = self.books.add("978-8880000017", "Renew Book", "Auth", 1, 2024, 1)
        mid = self.members.add("MT17", "Renew Member", "mt17@meridian.edu", "2026-11-01")
        lid = self.loans.issue_book_safe(mid, bid, "2026-11-01")
        self.assertTrue(self.loans.renew_loan(lid))
        self.assertTrue(self.loans.renew_loan(lid))
        with self.assertRaises(ValueError):
            self.loans.renew_loan(lid)

    def test_18_safe_delete_member_refused_with_active_loan(self):
        with self.assertRaises(PermissionError):
            safe_delete_member(self.DB_TYPE, 1)

    def test_19_safe_delete_member_audited_success(self):
        mid = self.members.add("MT19", "Del Member", "mt19@meridian.edu", "2026-11-01")
        ok, _ = safe_delete_member(self.DB_TYPE, mid)
        self.assertTrue(ok)
        self.assertIsNone(self.members.get_by_id(mid))

    def test_20_transaction_rollback_preserves_counts(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM category")
        before = cur.fetchone()[0]
        cur.execute(self.d.sql("INSERT INTO category (name) VALUES ({ph})"), ("TempCatRollback",))
        self.conn.rollback()
        cur.execute("SELECT COUNT(*) FROM category")
        after = cur.fetchone()[0]
        cur.close()
        self.assertEqual(before, after)

    def test_21_connection_error_classification(self):
        self.assertTrue(is_transient_error("sqlite", sqlite3.OperationalError("database is locked")))
        self.assertFalse(is_transient_error("sqlite", sqlite3.OperationalError("unable to open database file")))

    def test_22_safe_connect_retries_transient_only(self):
        calls = {"n": 0}
        def flaky(_db):
            calls["n"] += 1
            if calls["n"] < 2:
                raise sqlite3.OperationalError("database is locked")
            return sqlite3.connect(":memory:")
        c = safe_connect("sqlite", retries=2, delay=0.01, connector_fn=flaky)
        c.close()
        self.assertEqual(calls["n"], 2)


class TestSQLiteCRUD(BaseMeridianCRUDTests, unittest.TestCase):
    DB_TYPE = "sqlite"


class TestMySQLCRUD(BaseMeridianCRUDTests, unittest.TestCase):
    DB_TYPE = "mysql"


class TestPostgresCRUD(BaseMeridianCRUDTests, unittest.TestCase):
    DB_TYPE = "postgres"


if __name__ == "__main__":
    unittest.main(verbosity=2)

