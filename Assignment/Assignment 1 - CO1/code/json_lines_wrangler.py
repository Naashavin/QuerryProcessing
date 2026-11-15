import csv
import json
import re
import sqlite3
from config import (
    DB_PATH,
    DB_V2_PATH,
    RAW_JSONL_PATH,
    TELE_CLEAN_CSV_PATH,
    TELE_REJECTED_CSV_PATH,
)
from utils import normalise_patient_id, parse_eu_amount, standardise_name, utc_to_ist


REVISED_DDL = """
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
    patient_id VARCHAR(12) PRIMARY KEY,
    legacy_id VARCHAR(12),
    full_name VARCHAR(80) NOT NULL,
    gender CHAR(1) CHECK (gender IN ('M', 'F', 'O') OR gender IS NULL),
    date_of_birth DATE,
    phone VARCHAR(15),
    registered_on DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS VISIT (
    visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id VARCHAR(12) NOT NULL,
    doctor_id VARCHAR(12),
    department_id INTEGER NOT NULL,
    visit_date DATE NOT NULL,
    visit_mode VARCHAR(12) NOT NULL CHECK (visit_mode IN ('IN_PERSON', 'TELE')),
    fee_amount DECIMAL(8,2) CHECK (fee_amount >= 0),
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id),
    FOREIGN KEY (doctor_id) REFERENCES DOCTOR(doctor_id),
    FOREIGN KEY (department_id) REFERENCES DEPARTMENT(department_id)
);

CREATE TABLE IF NOT EXISTS TELE_SESSION (
    session_id VARCHAR(20) PRIMARY KEY,
    visit_id INTEGER NOT NULL,
    start_time_ist DATETIME NOT NULL,
    duration_min INTEGER CHECK (duration_min >= 0),
    prescribed_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (visit_id) REFERENCES VISIT(visit_id)
);
"""


def normalise_national_id(val):
    if not val:
        return None
    text = str(val).strip().upper()
    if re.fullmatch(r"PT-\d{6}", text):
        return text
    return None


def wrangle_jsonl_streaming(
    raw_path=RAW_JSONL_PATH,
    clean_csv=TELE_CLEAN_CSV_PATH,
    rejected_csv=TELE_REJECTED_CSV_PATH,
):
    """Stream Source D line by line, flatten, convert UTC->IST, parse EU fees, reject malformed lines."""
    clean_csv.parent.mkdir(parents=True, exist_ok=True)
    clean_fields = [
        "session_id", "national_id", "legacy_id", "patient_name",
        "start_time_ist", "visit_date_ist", "duration_min",
        "consultation_fee", "fee_missing", "doctor_id",
        "speciality", "prescribed_count",
    ]
    rej_fields = ["line_no", "raw_snippet", "rejection_reason"]

    total_lines = 0
    clean_count = 0
    rejected_count = 0
    null_fee_count = 0
    missing_doc_count = 0

    with (
        open(raw_path, "r", encoding="utf-8") as fin,
        open(clean_csv, "w", encoding="utf-8", newline="") as fclean,
        open(rejected_csv, "w", encoding="utf-8", newline="") as frej,
    ):
        cw = csv.DictWriter(fclean, fieldnames=clean_fields)
        cw.writeheader()
        rw = csv.DictWriter(frej, fieldnames=rej_fields)
        rw.writeheader()

        for line_no, line in enumerate(fin, start=1):
            raw_line = line.strip()
            if not raw_line:
                continue
            total_lines += 1

            try:
                rec = json.loads(raw_line)
            except json.JSONDecodeError as err:
                rejected_count += 1
                rw.writerow({
                    "line_no": line_no,
                    "raw_snippet": raw_line[:80],
                    "rejection_reason": f"JSON_DECODE_ERROR: {err.msg}",
                })
                continue

            sid = (rec.get("session_id") or "").strip()
            pat = rec.get("patient") or {}
            nat_id = normalise_national_id(pat.get("national_id"))
            leg_canon, _ = normalise_patient_id(pat.get("legacy_id"))
            name_obj = pat.get("name") or {}
            full_name = standardise_name(f"{name_obj.get('first', '')} {name_obj.get('last', '')}")

            ist_iso, ist_date = utc_to_ist(rec.get("start_time"))

            if not sid:
                rejected_count += 1
                rw.writerow({"line_no": line_no, "raw_snippet": raw_line[:80], "rejection_reason": "MISSING_SESSION_ID"})
                continue
            if not nat_id:
                rejected_count += 1
                rw.writerow({"line_no": line_no, "raw_snippet": raw_line[:80], "rejection_reason": "INVALID_NATIONAL_ID"})
                continue
            if not ist_iso:
                rejected_count += 1
                rw.writerow({"line_no": line_no, "raw_snippet": raw_line[:80], "rejection_reason": "INVALID_TIMESTAMP"})
                continue

            try:
                dur = int(rec.get("duration_min"))
            except (TypeError, ValueError):
                dur = 0

            fee = parse_eu_amount(rec.get("consultation_fee"))
            if fee is None:
                null_fee_count += 1

            doc = rec.get("doctor")
            if not isinstance(doc, dict):
                missing_doc_count += 1
                doc_id = ""
                spec = "UNKNOWN"
            else:
                doc_id = (doc.get("doctor_id") or "").strip()
                spec = (doc.get("speciality") or "UNKNOWN").strip()

            prescribed = rec.get("prescribed") or []
            cw.writerow({
                "session_id": sid,
                "national_id": nat_id,
                "legacy_id": leg_canon or "",
                "patient_name": full_name or "Unknown",
                "start_time_ist": ist_iso,
                "visit_date_ist": ist_date,
                "duration_min": dur,
                "consultation_fee": f"{fee:.2f}" if fee is not None else "",
                "fee_missing": str(fee is None),
                "doctor_id": doc_id,
                "speciality": spec,
                "prescribed_count": len(prescribed),
            })
            clean_count += 1

    return {
        "total_lines": total_lines,
        "clean_count": clean_count,
        "rejected_count": rejected_count,
        "null_fee_count": null_fee_count,
        "missing_doc_count": missing_doc_count,
    }


def migrate_and_load_v2(old_db=DB_PATH, new_db=DB_V2_PATH, tele_csv=TELE_CLEAN_CSV_PATH, tele_limit=500):
    """Migrate existing INT patients/visits to VARCHAR(12) schema and load TELE_SESSION sample."""
    if new_db.exists():
        new_db.unlink()
    v2 = sqlite3.connect(new_db)
    v2.executescript(REVISED_DDL)

    migrated_patients = 0
    migrated_visits = 0

    if old_db.exists():
        v1 = sqlite3.connect(old_db)
        v1.row_factory = sqlite3.Row

        for r in v1.execute("SELECT * FROM DEPARTMENT"):
            v2.execute("INSERT INTO DEPARTMENT VALUES (?, ?)", (r["department_id"], r["department_name"]))
        for r in v1.execute("SELECT * FROM DOCTOR"):
            v2.execute("INSERT INTO DOCTOR VALUES (?, ?, ?)", (r["doctor_id"], r["doctor_name"], r["department_id"]))

        for r in v1.execute("SELECT * FROM PATIENT"):
            new_pid = f"P{r['patient_id']}"
            v2.execute(
                "INSERT INTO PATIENT (patient_id, legacy_id, full_name, gender, date_of_birth, phone, registered_on) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_pid, new_pid, r["full_name"], r["gender"], r["date_of_birth"], r["phone"], r["registered_on"]),
            )
            migrated_patients += 1

        for r in v1.execute("SELECT * FROM VISIT"):
            new_pid = f"P{r['patient_id']}"
            v2.execute(
                "INSERT INTO VISIT (patient_id, doctor_id, department_id, visit_date, visit_mode, fee_amount) VALUES (?, ?, ?, ?, 'IN_PERSON', ?)",
                (new_pid, r["doctor_id"], r["department_id"], r["visit_date"], r["fee_amount"]),
            )
            migrated_visits += 1
        v1.close()

    dept_map = {"Cardiology": 1, "ENT": 2, "Orthopaedics": 3, "Paediatrics": 4, "General Medicine": 5}
    tele_loaded = 0

    with open(tele_csv, "r", encoding="utf-8", newline="") as f:
        for idx, row in enumerate(csv.DictReader(f)):
            if idx >= tele_limit:
                break
            nat_id = row["national_id"]
            # Insert patient if not already present
            exists = v2.execute("SELECT 1 FROM PATIENT WHERE patient_id = ?", (nat_id,)).fetchone()
            if not exists:
                v2.execute(
                    "INSERT INTO PATIENT (patient_id, legacy_id, full_name, gender, date_of_birth, phone, registered_on) VALUES (?, ?, ?, NULL, NULL, NULL, ?)",
                    (nat_id, row["legacy_id"] or None, row["patient_name"], row["visit_date_ist"]),
                )
            did = dept_map.get(row["speciality"], 5)
            doc_id = row["doctor_id"] if row["doctor_id"] else None
            fee_val = float(row["consultation_fee"]) if row["consultation_fee"] else 0.0
            cur = v2.execute(
                "INSERT INTO VISIT (patient_id, doctor_id, department_id, visit_date, visit_mode, fee_amount) VALUES (?, ?, ?, ?, 'TELE', ?)",
                (nat_id, doc_id, did, row["visit_date_ist"], fee_val),
            )
            vid = cur.lastrowid
            v2.execute(
                "INSERT INTO TELE_SESSION (session_id, visit_id, start_time_ist, duration_min, prescribed_count) VALUES (?, ?, ?, ?, ?)",
                (row["session_id"], vid, row["start_time_ist"], int(row["duration_min"]), int(row["prescribed_count"])),
            )
            tele_loaded += 1

    v2.commit()
    v2.close()
    return {"migrated_patients": migrated_patients, "migrated_visits": migrated_visits, "tele_loaded": tele_loaded}


if __name__ == "__main__":
    stats = wrangle_jsonl_streaming()
    print("=== Source D Streaming Wrangler Summary ===")
    print(stats)
    mig = migrate_and_load_v2()
    print("=== V2 Schema Migration & Load Summary ===")
    print(mig)

