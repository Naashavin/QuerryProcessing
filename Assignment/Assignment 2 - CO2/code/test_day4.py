import unittest
from contextlib import closing
from db_config import get_connection
from dedup_members import deduplicate_and_reconcile, generate_merged_branch_dataset
from dialect import Dialect
from repositories import BookRepository, LoanRepository, MemberRepository
from reservation_repo import ReservationRepository
from seed_data import seed_database


def backend_up(db_type):
    if db_type == "sqlite":
        return True
    try:
        with closing(get_connection(db_type)):
            return True
    except Exception:
        return False


class BaseDay4Tests:
    DB_TYPE = None

    @classmethod
    def setUpClass(cls):
        if not backend_up(cls.DB_TYPE):
            raise unittest.SkipTest(f"{cls.DB_TYPE} server not running.")
        seed_database(cls.DB_TYPE, seed=42)

    def setUp(self):
        self.d = Dialect(self.DB_TYPE)
        self.conn = get_connection(self.DB_TYPE)
        self.members = MemberRepository(self.conn, self.d)
        self.books = BookRepository(self.conn, self.d)
        self.loans = LoanRepository(self.conn, self.d)
        self.res_repo = ReservationRepository(self.conn, self.d)
        self.res_repo.ensure_table()

    def tearDown(self):
        self.conn.close()

    def test_01_rr1_cannot_reserve_when_copies_available(self):
        bid = self.books.add("978-6660000001", "RR1 Avail Book", "Author", 1, 2024, 1)
        mid = self.members.add("D4M1", "RR1 Member", "d4m1@meridian.edu", "2026-11-01")
        with self.assertRaises(ValueError):
            self.res_repo.create_reservation(mid, bid)

    def test_02_rr1_rr2_rr3_full_reservation_lifecycle(self):
        bid = self.books.add("978-6660000002", "RR23 Book", "Author", 1, 2024, 1)
        m1 = self.members.add("D4M2", "Borrower", "d4m2@meridian.edu", "2026-11-01")
        m2 = self.members.add("D4M3", "Waiter 1", "d4m3@meridian.edu", "2026-11-01")
        m3 = self.members.add("D4M4", "Waiter 2", "d4m4@meridian.edu", "2026-11-01")

        # Borrow last copy -> copies_available = 0
        lid = self.loans.issue_book_safe(m1, bid, "2026-11-01")

        # RR1 satisfied: m2 and m3 can reserve
        r1 = self.res_repo.create_reservation(m2, bid)
        r2 = self.res_repo.create_reservation(m3, bid)
        self.assertGreater(r1, 0)

        # RR2 enforced: m2 cannot create second active reservation for same book
        with self.assertRaises(ValueError):
            self.res_repo.create_reservation(m2, bid)

        # RR3 enforced: returning loan marks earliest WAITING reservation (r1) as READY
        promoted = self.res_repo.return_book_and_notify_next(lid, "2026-11-05")
        self.assertEqual(promoted, r1)
        rows = self.res_repo.get_by_book(bid)
        status_map = {r["reservation_id"]: r["status"] for r in rows}
        self.assertEqual(status_map[r1], "READY")
        self.assertEqual(status_map[r2], "WAITING")

    def test_03_rr4_cascade_delete_no_orphan_reservations(self):
        bid = self.books.add("978-6660000003", "RR4 Book", "Author", 1, 2024, 1)
        m_borrow = self.members.add("D4M5", "RR4 Borrower", "d4m5@meridian.edu", "2026-11-01")
        m_wait = self.members.add("D4M6", "RR4 Waiter", "d4m6@meridian.edu", "2026-11-01")
        self.loans.issue_book_safe(m_borrow, bid, "2026-11-01")
        self.res_repo.create_reservation(m_wait, bid)

        # Delete waiting member (no active loans/fines) -> ON DELETE CASCADE cleans reservation
        self.members.safe_delete(m_wait)
        self.assertEqual(len(self.res_repo.get_by_book(bid)), 0)


class TestDay4DedupScale(unittest.TestCase):
    def test_dedup_and_orphan_quarantine(self):
        m_raw, l_raw = generate_merged_branch_dataset(num_unique_members=500, num_loans=1000, seed=42)
        res = deduplicate_and_reconcile(m_raw, l_raw)
        self.assertEqual(len(res["clean_members"]), 500)
        self.assertEqual(res["duplicates_merged"], 50)
        self.assertEqual(len(res["orphan_loans"]), 60)


class TestDay4SQLite(BaseDay4Tests, unittest.TestCase):
    DB_TYPE = "sqlite"


class TestDay4MySQL(BaseDay4Tests, unittest.TestCase):
    DB_TYPE = "mysql"


class TestDay4Postgres(BaseDay4Tests, unittest.TestCase):
    DB_TYPE = "postgres"


if __name__ == "__main__":
    unittest.main(verbosity=2)
