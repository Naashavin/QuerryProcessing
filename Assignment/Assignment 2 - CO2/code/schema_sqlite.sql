PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS reservation;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS fine;
DROP TABLE IF EXISTS loan;
DROP TABLE IF EXISTS member;
DROP TABLE IF EXISTS book;
DROP TABLE IF EXISTS category;

CREATE TABLE category (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE book (
    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(150) NOT NULL,
    author VARCHAR(100) NOT NULL,
    category_id INTEGER NOT NULL,
    publication_year INTEGER NOT NULL CHECK (publication_year BETWEEN 1450 AND 2100),
    copies_total INTEGER NOT NULL CHECK (copies_total >= 0),
    copies_available INTEGER NOT NULL CHECK (copies_available >= 0 AND copies_available <= copies_total),
    FOREIGN KEY (category_id) REFERENCES category(category_id) ON DELETE RESTRICT
);

CREATE TABLE member (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_code VARCHAR(20) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL CHECK (LENGTH(TRIM(full_name)) > 0),
    email VARCHAR(120) NOT NULL UNIQUE CHECK (email LIKE '%@%.%'),
    joined_on DATE NOT NULL,
    status VARCHAR(15) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'EXPIRED', 'DELETED'))
);

CREATE TABLE loan (
    loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    issued_on DATE NOT NULL,
    due_on DATE NOT NULL CHECK (due_on >= issued_on),
    returned_on DATE,
    renew_count INTEGER NOT NULL DEFAULT 0 CHECK (renew_count BETWEEN 0 AND 2),
    FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE RESTRICT,
    FOREIGN KEY (book_id) REFERENCES book(book_id) ON DELETE RESTRICT
);

CREATE TABLE fine (
    fine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id INTEGER NOT NULL UNIQUE,
    amount DECIMAL(8,2) NOT NULL CHECK (amount >= 0),
    assessed_on DATE NOT NULL,
    paid INTEGER NOT NULL DEFAULT 0 CHECK (paid IN (0, 1)),
    FOREIGN KEY (loan_id) REFERENCES loan(loan_id) ON DELETE CASCADE
);

CREATE TABLE audit_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name VARCHAR(50) NOT NULL,
    record_key VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    details TEXT,
    logged_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

