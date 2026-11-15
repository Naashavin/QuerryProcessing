-- Day-4 PostgreSQL Reservation Extension & Performance Indexes (RR1–RR4)

CREATE TABLE IF NOT EXISTS reservation (
    reservation_id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES member(member_id) ON DELETE CASCADE,
    book_id INTEGER NOT NULL REFERENCES book(book_id) ON DELETE CASCADE,
    reserved_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(15) NOT NULL DEFAULT 'WAITING'
        CHECK (status IN ('WAITING', 'READY', 'FULFILLED', 'CANCELLED'))
);

-- RR2: At most one active (WAITING or READY) reservation per member per book
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_reservation
    ON reservation(member_id, book_id)
    WHERE status IN ('WAITING', 'READY');

-- Day-4 Scale Indexes for 100,000+ loans
CREATE INDEX IF NOT EXISTS idx_loan_member ON loan(member_id);
CREATE INDEX IF NOT EXISTS idx_loan_book ON loan(book_id);
CREATE INDEX IF NOT EXISTS idx_loan_unreturned_due ON loan(due_on) WHERE returned_on IS NULL;

