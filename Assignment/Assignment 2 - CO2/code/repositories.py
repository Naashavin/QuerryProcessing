import json
from datetime import date, timedelta
from dialect import Dialect


class MemberRepository:
    def __init__(self, conn, dialect: Dialect):
        self.conn = conn
        self.d = dialect

    def add(self, member_code, full_name, email, joined_on, status="ACTIVE"):
        cur = self.d.cursor(self.conn)
        try:
            mid = self.d.insert_returning_id(
                cur,
                "INSERT INTO member (member_code, full_name, email, joined_on, status) "
                "VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
                (member_code, full_name.strip(), email.strip().lower(), joined_on, status),
                "member_id",
            )
            self.conn.commit()
            return mid
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def get_by_id(self, member_id):
        cur = self.d.cursor(self.conn, as_dict=True)
        cur.execute(self.d.sql("SELECT * FROM member WHERE member_id = {ph}"), (member_id,))
        row = self.d.fetch_one_dict(cur)
        cur.close()
        return row

    def safe_delete(self, member_id):
        cur = self.d.cursor(self.conn, as_dict=True)
        try:
            cur.execute(self.d.sql("SELECT * FROM member WHERE member_id = {ph}"), (member_id,))
            mem = self.d.fetch_one_dict(cur)
            if not mem:
                raise LookupError(f"Member {member_id} not found.")

            cur.execute(
                self.d.sql("SELECT COUNT(*) AS cnt FROM loan WHERE member_id = {ph} AND returned_on IS NULL"),
                (member_id,),
            )
            if self.d.fetch_one_dict(cur)["cnt"] > 0:
                raise PermissionError(f"Member {member_id} has unreturned loans (BR9).")

            cur.execute(
                self.d.sql(
                    "SELECT COUNT(*) AS cnt FROM fine f JOIN loan l ON f.loan_id = l.loan_id "
                    "WHERE l.member_id = {ph} AND f.paid = {ph}"
                ),
                (member_id, self.d.bool_val(False)),
            )
            if self.d.fetch_one_dict(cur)["cnt"] > 0:
                raise PermissionError(f"Member {member_id} has unpaid fines (BR9).")

            snapshot = {k: str(v) for k, v in mem.items()}
            cur.execute(
                self.d.sql("INSERT INTO audit_log (table_name, record_key, action, details) VALUES ({ph}, {ph}, {ph}, {ph})"),
                ("member", str(member_id), "HARD_DELETE", json.dumps(snapshot)),
            )
            cur.execute(self.d.sql("DELETE FROM member WHERE member_id = {ph}"), (member_id,))
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()


class BookRepository:
    def __init__(self, conn, dialect: Dialect):
        self.conn = conn
        self.d = dialect

    def add(self, isbn, title, author, category_id, publication_year, copies_total):
        cur = self.d.cursor(self.conn)
        try:
            bid = self.d.insert_returning_id(
                cur,
                "INSERT INTO book (isbn, title, author, category_id, publication_year, copies_total, copies_available) "
                "VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                (isbn, title.strip(), author.strip(), category_id, publication_year, copies_total, copies_total),
                "book_id",
            )
            self.conn.commit()
            return bid
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def search(self, keyword):
        cur = self.d.cursor(self.conn, as_dict=True)
        sql = (
            f"SELECT b.book_id, b.isbn, b.title, b.author, c.name AS category, b.copies_available "
            f"FROM book b JOIN category c ON b.category_id = c.category_id "
            f"WHERE {self.d.ilike('b.title')} OR {self.d.ilike('b.author')} ORDER BY b.title"
        )
        pat = f"%{keyword}%"
        cur.execute(sql, (pat, pat))
        rows = self.d.fetch_dicts(cur)
        cur.close()
        return rows


class LoanRepository:
    def __init__(self, conn, dialect: Dialect):
        self.conn = conn
        self.d = dialect

    def issue_book(self, member_id, book_id, issued_on=None):
        """Original read-then-update issue_book (checks BR7 and availability, updates stock)."""
        issued_d = date.fromisoformat(issued_on) if issued_on else date.today()
        due_d = issued_d + timedelta(days=14)
        cur = self.d.cursor(self.conn, as_dict=True)
        try:
            cur.execute(
                self.d.sql("SELECT COUNT(*) AS cnt FROM loan WHERE member_id = {ph} AND returned_on IS NULL"),
                (member_id,),
            )
            if self.d.fetch_one_dict(cur)["cnt"] >= 3:
                raise ValueError("BR7: Member already holds 3 unreturned loans.")

            cur.execute(self.d.sql("SELECT copies_available FROM book WHERE book_id = {ph}"), (book_id,))
            bk = self.d.fetch_one_dict(cur)
            if not bk or bk["copies_available"] <= 0:
                raise ValueError("No copies available for this book.")

            cur.execute(
                self.d.sql("UPDATE book SET copies_available = copies_available - 1 WHERE book_id = {ph}"),
                (book_id,),
            )
            lid = self.d.insert_returning_id(
                cur,
                "INSERT INTO loan (member_id, book_id, issued_on, due_on) VALUES ({ph}, {ph}, {ph}, {ph})",
                (member_id, book_id, issued_d.isoformat(), due_d.isoformat()),
                "loan_id",
            )
            self.conn.commit()
            return lid
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def issue_book_safe(self, member_id, book_id, issued_on=None):
        """Concurrency-safe Day-4 version using conditional UPDATE ... WHERE copies_available > 0."""
        issued_d = date.fromisoformat(issued_on) if issued_on else date.today()
        due_d = issued_d + timedelta(days=14)
        cur = self.d.cursor(self.conn, as_dict=True)
        try:
            cur.execute(
                self.d.sql("SELECT COUNT(*) AS cnt FROM loan WHERE member_id = {ph} AND returned_on IS NULL"),
                (member_id,),
            )
            if self.d.fetch_one_dict(cur)["cnt"] >= 3:
                raise ValueError("BR7: Member already holds 3 unreturned loans.")

            cur.execute(
                self.d.sql(
                    "UPDATE book SET copies_available = copies_available - 1 "
                    "WHERE book_id = {ph} AND copies_available > 0"
                ),
                (book_id,),
            )
            if cur.rowcount != 1:
                raise ValueError("No copies available (atomic conditional update prevented oversell).")

            lid = self.d.insert_returning_id(
                cur,
                "INSERT INTO loan (member_id, book_id, issued_on, due_on) VALUES ({ph}, {ph}, {ph}, {ph})",
                (member_id, book_id, issued_d.isoformat(), due_d.isoformat()),
                "loan_id",
            )
            self.conn.commit()
            return lid
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def return_book(self, loan_id, returned_on=None):
        ret_d = date.fromisoformat(returned_on) if returned_on else date.today()
        cur = self.d.cursor(self.conn, as_dict=True)
        try:
            cur.execute(self.d.sql("SELECT * FROM loan WHERE loan_id = {ph}"), (loan_id,))
            ln = self.d.fetch_one_dict(cur)
            if not ln or ln["returned_on"] is not None:
                raise ValueError(f"Loan {loan_id} not active or already returned.")

            cur.execute(
                self.d.sql("UPDATE loan SET returned_on = {ph} WHERE loan_id = {ph} AND returned_on IS NULL"),
                (ret_d.isoformat(), loan_id),
            )
            cur.execute(
                self.d.sql("UPDATE book SET copies_available = copies_available + 1 WHERE book_id = {ph}"),
                (ln["book_id"],),
            )

            due_d = ln["due_on"] if isinstance(ln["due_on"], date) else date.fromisoformat(str(ln["due_on"]))
            fine_amt = 0.0
            if ret_d > due_d:
                fine_amt = round((ret_d - due_d).days * 2.0, 2)
                cur.execute(
                    self.d.sql("INSERT INTO fine (loan_id, amount, assessed_on, paid) VALUES ({ph}, {ph}, {ph}, {ph})"),
                    (loan_id, fine_amt, ret_d.isoformat(), self.d.bool_val(False)),
                )
            self.conn.commit()
            return fine_amt
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def renew_loan(self, loan_id):
        cur = self.d.cursor(self.conn)
        try:
            new_due = self.d.add_days_expr("due_on", 7)
            cur.execute(
                self.d.sql(
                    f"UPDATE loan SET due_on = {new_due}, renew_count = renew_count + 1 "
                    f"WHERE loan_id = {{ph}} AND returned_on IS NULL AND renew_count < 2"
                ),
                (loan_id,),
            )
            if cur.rowcount != 1:
                raise ValueError(f"Cannot renew loan {loan_id}: already returned or max renewals (2) reached (BR11).")
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def overdue_report(self):
        cur = self.d.cursor(self.conn, as_dict=True)
        today = self.d.today_expr()
        cur.execute(
            f"SELECT l.loan_id, m.member_code, m.full_name, b.title, l.due_on "
            f"FROM loan l JOIN member m ON l.member_id = m.member_id "
            f"JOIN book b ON l.book_id = b.book_id "
            f"WHERE l.returned_on IS NULL AND l.due_on < {today} ORDER BY l.due_on"
        )
        rows = self.d.fetch_dicts(cur)
        cur.close()
        return rows

