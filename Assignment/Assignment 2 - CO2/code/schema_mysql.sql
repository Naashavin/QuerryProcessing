SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS reservation;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS fine;
DROP TABLE IF EXISTS loan;
DROP TABLE IF EXISTS member;
DROP TABLE IF EXISTS book;
DROP TABLE IF EXISTS category;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE category (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE book (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    isbn VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(150) NOT NULL,
    author VARCHAR(100) NOT NULL,
    category_id INT NOT NULL,
    publication_year INT NOT NULL CHECK (publication_year BETWEEN 1450 AND 2100),
    copies_total INT NOT NULL CHECK (copies_total >= 0),
    copies_available INT NOT NULL,
    CONSTRAINT chk_book_copies CHECK (copies_available >= 0 AND copies_available <= copies_total),
    CONSTRAINT fk_book_category FOREIGN KEY (category_id) REFERENCES category(category_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE member (
    member_id INT AUTO_INCREMENT PRIMARY KEY,
    member_code VARCHAR(20) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL CHECK (CHAR_LENGTH(TRIM(full_name)) > 0),
    email VARCHAR(120) NOT NULL UNIQUE CHECK (email LIKE '%@%.%'),
    joined_on DATE NOT NULL,
    status VARCHAR(15) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'EXPIRED', 'DELETED'))
) ENGINE=InnoDB;

CREATE TABLE loan (
    loan_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    book_id INT NOT NULL,
    issued_on DATE NOT NULL,
    due_on DATE NOT NULL,
    returned_on DATE NULL,
    renew_count INT NOT NULL DEFAULT 0 CHECK (renew_count BETWEEN 0 AND 2),
    CONSTRAINT chk_loan_dates CHECK (due_on >= issued_on),
    CONSTRAINT fk_loan_member FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE RESTRICT,
    CONSTRAINT fk_loan_book FOREIGN KEY (book_id) REFERENCES book(book_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE fine (
    fine_id INT AUTO_INCREMENT PRIMARY KEY,
    loan_id INT NOT NULL UNIQUE,
    amount DECIMAL(8,2) NOT NULL CHECK (amount >= 0),
    assessed_on DATE NOT NULL,
    paid TINYINT(1) NOT NULL DEFAULT 0 CHECK (paid IN (0, 1)),
    CONSTRAINT fk_fine_loan FOREIGN KEY (loan_id) REFERENCES loan(loan_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE audit_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_key VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    details TEXT,
    logged_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
