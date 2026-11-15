from datetime import date
from dialect import Dialect


RESERVATION_DDL_GENERIC = {
    "sqlite": """
        CREATE TABLE IF NOT EXISTS reservation (
            reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL REFERENCES member(member_id) ON DELETE CASCADE,
            book_id INTEGER NOT NULL REFERENCES book(book_id) ON DELETE CASCADE,
            reserved_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(15) NOT NULL DEFAULT 'WAITING'
                CHECK (status IN ('WAITING', 'READY', 'FULFILLED', 'CANCELLED'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_reservation
            ON reservation(member_id, book_id) WHERE status IN ('WAITING', 'READY');
    """,
    "mysql": """
        CREATE TABLE IF NOT EXISTS reservation (
            reservation_id INT AUTO_INCREMENT PRIMARY KEY,
            member_id INT NOT NULL,
            book_id INT NOT NULL,
            reserved_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(15) NOT NULL DEFAULT 'WAITING'
                CHECK (status IN ('WAITING', 'READY', 'FULFILLED', 'CANCELLED')),
            CONSTRAINT fk_res_member FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE CASCADE,
            CONSTRAINT fk_res_book FOREIGN KEY (book_id) REFERENCES book(book_id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
    """,
    "postgres": """
        CREATE TABLE IF NOT EXISTS reservation (
            reservation_id SERIAL PRIMARY KEY,
            member_id INTEGER NOT NULL REFERENCES member(member_id) ON DELETE CASCADE,
            book_id INTEGER NOT NULL REFERENCES book(book_id) ON DELETE CASCADE,
            reserved_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(15) NOT NULL DEFAULT 'WAITING'
                CHECK (status IN ('WAITING', 'READY', 'FULFILLED', 'CANCELLED'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_reservation
            ON reservation(member_id, book_id) WHERE status IN ('WAITING', 'READY');
    """,
}


class ReservationRepository:
    """CRUD & RR1-RR4 business rules for Day-4 Reservation entity."""

    def __init__(self, conn, dialect: Dialect):
        self.conn = conn
        self.d = dialect

    def ensure_table(self):
        cur = self.d.cursor(self.conn)
        ddl = RESERVATION_DDL_GENERIC[self.d.db_type]
        if self.d.db_type == "sqlite":
            self.conn.executescript(ddl)
        else:
            for stmt in [s.strip() for s in ddl.split(";") if s.strip()]:
                cur.execute(stmt)
            self.conn.commit()
        cur.close()

    def create_reservation(self, member_id, book_id):
        """Enforce RR1 (copies_available == 0) and RR2 (max 1 active reservation per member/book)."""
        cur = self.d.cursor(self.conn, as_dict=True)
        try:
            # RR1 check
            cur.execute(self.d.sql("SELECT copies_available FROM book WHERE book_id = {ph}"), (book_id,))
            bk = self.d.fetch_one_dict(cur)
            if not bk:
                raise LookupError(f"Book {book_id} not found.")
            if bk["copies_available"] > 0:
                raise ValueError(f"RR1 violated: Book {book_id} has {bk['copies_available']} copy(s) available; borrow directly.")

            # RR2 check
            cur.execute(
                self.d.sql(
                    "SELECT reservation_id FROM reservation "
                    "WHERE member_id = {ph} AND book_id = {ph} AND status IN ('WAITING', 'READY')"
                ),
                (member_id, book_id),
            )
            if self.d.fetch_one_dict(cur):
                raise ValueError(f"RR2 violated: Member {member_id} already has an active reservation for Book {book_id}.")

            res_id = self.d.insert_returning_id(
                cur,
                "INSERT INTO reservation (member_id, book_id, status) VALUES ({ph}, {ph}, 'WAITING')",
                (member_id, book_id),
                "reservation_id",
            )
            self.conn.commit()
            return res_id
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def get_by_book(self, book_id):
        cur = self.d.cursor(self.conn, as_dict=True)
        cur.execute(
            self.d.sql("SELECT * FROM reservation WHERE book_id = {ph} ORDER BY reservation_id"),
            (book_id,),
        )
        rows = self.d.fetch_dicts(cur)
        cur.close()
        return rows

    def update_status(self, reservation_id, new_status):
        cur = self.d.cursor(self.conn)
        cur.execute(
            self.d.sql("UPDATE reservation SET status = {ph} WHERE reservation_id = {ph}"),
            (new_status, reservation_id),
        )
        rc = cur.rowcount
        self.conn.commit()
        cur.close()
        return rc

    def cancel_reservation(self, reservation_id):
        return self.update_status(reservation_id, "CANCELLED")

    def delete_reservation(self, reservation_id):
        cur = self.d.cursor(self.conn)
        cur.execute(self.d.sql("DELETE FROM reservation WHERE reservation_id = {ph}"), (reservation_id,))
        rc = cur.rowcount
        self.conn.commit()
        cur.close()
        return rc

    def return_book_and_notify_next(self, loan_id, returned_on=None):
        """Return loan and fulfill RR3: mark earliest WAITING reservation as READY."""
        ret_d = returned_on or date.today().isoformat()
        cur = self.d.cursor(self.conn, as_dict=True)
        try:
            cur.execute(self.d.sql("SELECT * FROM loan WHERE loan_id = {ph}"), (loan_id,))
            ln = self.d.fetch_one_dict(cur)
            if not ln or ln["returned_on"] is not None:
                raise ValueError(f"Loan {loan_id} invalid or already returned.")

            cur.execute(
                self.d.sql("UPDATE loan SET returned_on = {ph} WHERE loan_id = {ph} AND returned_on IS NULL"),
                (ret_d, loan_id),
            )
            cur.execute(
                self.d.sql("UPDATE book SET copies_available = copies_available + 1 WHERE book_id = {ph}"),
                (ln["book_id"],),
            )

            # RR3: promote earliest WAITING reservation to READY
            cur.execute(
                self.d.sql(
                    "SELECT reservation_id, member_id FROM reservation "
                    "WHERE book_id = {ph} AND status = 'WAITING' ORDER BY reservation_id LIMIT 1"
                ),
                (ln["book_id"],),
            )
            nxt = self.d.fetch_one_dict(cur)
            promoted_id = None
            if nxt:
                cur.execute(
                    self.d.sql("UPDATE reservation SET status = 'READY' WHERE reservation_id = {ph}"),
                    (nxt["reservation_id"],),
                )
                promoted_id = nxt["reservation_id"]

            self.conn.commit()
            return promoted_id
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

