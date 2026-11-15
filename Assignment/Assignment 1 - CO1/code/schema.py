import sqlite3
from config import DB_PATH


DDL_STATEMENTS = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS DEPARTMENT (
    department_id INTEGER PRIMARY KEY,
    department_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS DOCTOR (
    doctor_id VARCHAR(12) PRIMARY KEY,
    doctor_name VARCHAR(80) NOT NULL,
    department_id INTEGER NOT NULL,
    FOREIGN KEY (department_id) REFERENCES DEPARTMENT(department_id)
);

CREATE TABLE IF NOT EXISTS PATIENT (
    patient_id INTEGER PRIMARY KEY,
    full_name VARCHAR(80) NOT NULL,
    gender CHAR(1) NOT NULL CHECK (gender IN ('M', 'F', 'O')),
    date_of_birth DATE,
    phone VARCHAR(15),
    registered_on DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS VISIT (
    visit_id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    doctor_id VARCHAR(12),
    department_id INTEGER NOT NULL,
    visit_date DATE NOT NULL,
    fee_amount DECIMAL(8,2) NOT NULL CHECK (fee_amount >= 0),
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id),
    FOREIGN KEY (doctor_id) REFERENCES DOCTOR(doctor_id),
    FOREIGN KEY (department_id) REFERENCES DEPARTMENT(department_id)
);

CREATE TABLE IF NOT EXISTS LAB_REPORT (
    report_id VARCHAR(25) PRIMARY KEY,
    visit_id INTEGER NOT NULL,
    collected_at DATETIME NOT NULL,
    status VARCHAR(15) NOT NULL CHECK (status IN ('FINAL', 'IN_PROGRESS', 'UNKNOWN')),
    FOREIGN KEY (visit_id) REFERENCES VISIT(visit_id)
);

CREATE TABLE IF NOT EXISTS LAB_RESULT (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id VARCHAR(25) NOT NULL,
    test_code VARCHAR(10) NOT NULL,
    result_value VARCHAR(20),
    result_num REAL,
    unit VARCHAR(15),
    flag VARCHAR(10) CHECK (flag IN ('LOW', 'NORMAL', 'HIGH', 'UNKNOWN')),
    FOREIGN KEY (report_id) REFERENCES LAB_REPORT(report_id)
);

CREATE TABLE IF NOT EXISTS PRESCRIPTION (
    rx_id VARCHAR(15) PRIMARY KEY,
    visit_id INTEGER NOT NULL,
    dispensed_on DATE NOT NULL,
    total_amount DECIMAL(8,2) NOT NULL CHECK (total_amount >= 0),
    FOREIGN KEY (visit_id) REFERENCES VISIT(visit_id)
);

CREATE TABLE IF NOT EXISTS RX_ITEM (
    rx_id VARCHAR(15) NOT NULL,
    drug_code VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(6,2) NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (rx_id, drug_code),
    FOREIGN KEY (rx_id) REFERENCES PRESCRIPTION(rx_id)
);
"""


def init_db(db_path=DB_PATH, reset=False):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if reset and db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DDL_STATEMENTS)
    conn.commit()
    return conn


def demonstrate_constraints():
    # Use a temporary test DB in memory or curated/schema_test.db
    test_conn = sqlite3.connect(":memory:")
    test_conn.execute("PRAGMA foreign_keys = ON;")
    test_conn.executescript(DDL_STATEMENTS)

    print("--- Inserting 5 Valid Records ---")
    valid_ops = [
        ("Valid Dept", "INSERT INTO DEPARTMENT VALUES (1, 'Cardiology')", ()),
        ("Valid Doctor", "INSERT INTO DOCTOR VALUES ('D-17', 'Dr. S. Meena', 1)", ()),
        ("Valid Patient", "INSERT INTO PATIENT VALUES (1001, 'Ravi Kumar', 'M', '1985-03-14', '9840012345', '2026-10-03')", ()),
        ("Valid Visit", "INSERT INTO VISIT VALUES (1, 1001, 'D-17', 1, '2026-10-03', 1200.50)", ()),
        ("Valid Rx", "INSERT INTO PRESCRIPTION VALUES ('RX-88121', 1, '2026-10-04', 90.00)", ()),
    ]
    for label, sql, params in valid_ops:
        test_conn.execute(sql, params)
        print(f"  [ACCEPTED] {label}")
    test_conn.commit()

    print("\n--- Testing 5 Deliberately Invalid Records ---")
    invalid_ops = [
        ("1. Duplicate PK (DEPARTMENT)", "INSERT INTO DEPARTMENT VALUES (1, 'Neurology')", ()),
        ("2. UNIQUE Violation (department_name)", "INSERT INTO DEPARTMENT VALUES (2, 'Cardiology')", ()),
        ("3. FK Violation (missing patient_id=9999)", "INSERT INTO VISIT VALUES (2, 9999, 'D-17', 1, '2026-10-03', 500)", ()),
        ("4. CHECK Constraint Violation (gender='X')", "INSERT INTO PATIENT VALUES (1002, 'Anitha S', 'X', '1990-07-21', NULL, '2026-10-03')", ()),
        ("5. NOT NULL Violation (full_name=NULL)", "INSERT INTO PATIENT VALUES (1003, NULL, 'F', '1999-12-31', NULL, '2026-10-05')", ()),
    ]
    for label, sql, params in invalid_ops:
        try:
            test_conn.execute(sql, params)
            print(f"  [UNEXPECTED ACCEPT] {label}")
        except sqlite3.IntegrityError as err:
            print(f"  [REJECTED] {label} -> sqlite3.IntegrityError: {err}")

    test_conn.close()


if __name__ == "__main__":
    demonstrate_constraints()

