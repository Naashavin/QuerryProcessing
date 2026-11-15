import csv
import json
import logging
import sqlite3
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from config import (
    CLEAN_CSV_PATH,
    CLEAN_XML_PATH,
    DB_PATH,
    LAB_FLAT_JSON_PATH,
    LOGS_DIR,
    RAW_CSV_PATH,
    RAW_JSON_PATH,
    RAW_XML_PATH,
)
from schema import init_db
from utils import normalise_patient_id


DEPARTMENTS_MASTER = {
    "Cardiology": 1,
    "ENT": 2,
    "Orthopaedics": 3,
    "Paediatrics": 4,
    "General Medicine": 5,
}

DOCTORS_MASTER = [
    ("D-17", "Dr. S. Meena", 1),
    ("D-31", "Dr. R. Karthik", 2),
    ("D-22", "Dr. V. Rajesh", 3),
    ("D-09", "Dr. P. Lakshmi", 4),
    ("D-14", "Dr. A. Suresh", 5),
]


def setup_logger():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("integrate")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fh = logging.FileHandler(LOGS_DIR / "integrate.log", mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    return logger


def count_id_normalization():
    """Count how many raw patient IDs across Sources A, B, C changed vs remained identical vs unresolved."""
    stats = {"total_seen": 0, "changed": 0, "unchanged": 0, "unresolved": 0}

    def check_val(raw_val):
        stats["total_seen"] += 1
        raw_s = (str(raw_val) if raw_val is not None else "").strip()
        canon_str, canon_int = normalise_patient_id(raw_s)
        if canon_int is None:
            stats["unresolved"] += 1
        elif raw_s == canon_str:
            stats["unchanged"] += 1
        else:
            stats["changed"] += 1

    with open(RAW_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if None in row:
                continue
            check_val(row.get("patient_id"))

    with open(RAW_JSON_PATH, "r", encoding="utf-8") as f:
        for rep in json.load(f):
            check_val(rep.get("patient_ref"))

    tree = ET.parse(RAW_XML_PATH)
    for disp in tree.getroot().findall("dispense"):
        pat = disp.find("patient")
        if pat is not None:
            check_val(pat.attrib.get("id"))

    return stats


def match_visit_by_date_proximity(patient_visits, target_date_str, window_days=7):
    """Return (status, visit_id) where status in {'matched', 'orphan', 'ambiguous'}."""
    if not patient_visits:
        return "orphan", None
    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
    candidates = []
    for vid, vdate_str in patient_visits:
        v_dt = datetime.strptime(vdate_str, "%Y-%m-%d")
        diff = abs((target_dt - v_dt).days)
        if diff <= window_days:
            # Slight preference for same-day or post-visit (target >= v_dt) on ties
            tie_break = 0 if target_dt >= v_dt else 1
            candidates.append((diff, tie_break, vid))

    if not candidates:
        return "orphan", None

    candidates.sort()
    best_diff = candidates[0][0]
    exact_ties = [c for c in candidates if c[0] == best_diff and c[1] == candidates[0][1]]
    if len(exact_ties) > 1:
        return "ambiguous", exact_ties[0][2]
    return "matched", candidates[0][2]


def run_integration(db_path=DB_PATH):
    logger = setup_logger()
    id_stats = count_id_normalization()
    conn = init_db(db_path, reset=True)
    cur = conn.cursor()

    loaded_counts = defaultdict(int)
    rejected_counts = defaultdict(int)

    # 1. Load Departments and Doctors
    for dname, did in DEPARTMENTS_MASTER.items():
        cur.execute("INSERT INTO DEPARTMENT (department_id, department_name) VALUES (?, ?)", (did, dname))
        loaded_counts["DEPARTMENT"] += 1

    for doc_id, doc_name, did in DOCTORS_MASTER:
        cur.execute("INSERT INTO DOCTOR (doctor_id, doctor_name, department_id) VALUES (?, ?, ?)", (doc_id, doc_name, did))
        loaded_counts["DOCTOR"] += 1

    dept_to_doc = {
        "Cardiology": "D-17",
        "ENT": "D-31",
        "Orthopaedics": "D-22",
        "Paediatrics": "D-09",
        "General Medicine": "D-14",
    }

    # 2. Load Patients and Visits from clean_visits.csv
    patient_visits_map = defaultdict(list)  # pid_int -> [(visit_id, visit_date)]
    seen_patients = set()
    visit_id_counter = 1

    with open(CLEAN_CSV_PATH, "r", encoding="utf-8", newline="") as f:
        visits = list(csv.DictReader(f))

    for row in visits:
        _, pid_int = normalise_patient_id(row["patient_id"])
        if pid_int is None:
            rejected_counts["PATIENT"] += 1
            continue

        if pid_int not in seen_patients:
            try:
                cur.execute(
                    """
                    INSERT INTO PATIENT (patient_id, full_name, gender, date_of_birth, phone, registered_on)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pid_int,
                        row["full_name"],
                        row["gender"],
                        row["dob"] if row["dob"] else None,
                        row["phone"] if row["phone"] else None,
                        row["visit_date"],
                    ),
                )
                seen_patients.add(pid_int)
                loaded_counts["PATIENT"] += 1
            except sqlite3.IntegrityError as err:
                rejected_counts["PATIENT"] += 1
                logger.warning(f"PATIENT {pid_int} rejected: {err}")
                continue

        dept_name = row["department"]
        dept_id = DEPARTMENTS_MASTER.get(dept_name, 5)
        doc_id = dept_to_doc.get(dept_name, "D-14")
        try:
            cur.execute(
                """
                INSERT INTO VISIT (visit_id, patient_id, doctor_id, department_id, visit_date, fee_amount)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (visit_id_counter, pid_int, doc_id, dept_id, row["visit_date"], float(row["fee_paid"])),
            )
            patient_visits_map[pid_int].append((visit_id_counter, row["visit_date"]))
            loaded_counts["VISIT"] += 1
            visit_id_counter += 1
        except sqlite3.IntegrityError as err:
            rejected_counts["VISIT"] += 1
            logger.warning(f"VISIT {visit_id_counter} rejected: {err}")

    # 3. Integrate Lab Reports & Results from staged/lab_results_flat.json
    with open(LAB_FLAT_JSON_PATH, "r", encoding="utf-8") as f:
        lab_rows = json.load(f)

    # Group flat rows by report_id to load LAB_REPORT then LAB_RESULT
    reports_grouped = defaultdict(list)
    for lr in lab_rows:
        reports_grouped[lr["report_id"]].append(lr)

    lab_link_stats = {"matched": 0, "orphan": 0, "ambiguous": 0}
    for rep_id, tests in reports_grouped.items():
        first = tests[0]
        _, pid_int = normalise_patient_id(first["patient_id"])
        status, visit_id = match_visit_by_date_proximity(patient_visits_map.get(pid_int, []), first["collected_date"])
        lab_link_stats[status] += 1

        if visit_id is None:
            # Demonstrate FK enforcement or skip orphan before load
            rejected_counts["LAB_REPORT"] += 1
            rejected_counts["LAB_RESULT"] += len(tests)
            logger.info(f"LAB_REPORT {rep_id} (patient {pid_int}): ORPHAN — skipped from DB load")
            continue

        has_pending = any(t["value_num"] is None for t in tests)
        rep_status = "IN_PROGRESS" if has_pending else "FINAL"
        try:
            cur.execute(
                "INSERT INTO LAB_REPORT (report_id, visit_id, collected_at, status) VALUES (?, ?, ?, ?)",
                (rep_id, visit_id, first["collected_date"], rep_status),
            )
            loaded_counts["LAB_REPORT"] += 1
        except sqlite3.IntegrityError as err:
            rejected_counts["LAB_REPORT"] += 1
            logger.warning(f"LAB_REPORT {rep_id} rejected: {err}")
            continue

        for t in tests:
            try:
                cur.execute(
                    """
                    INSERT INTO LAB_RESULT (report_id, test_code, result_value, result_num, unit, flag)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rep_id,
                        t["test_code"],
                        "pending" if t["value_num"] is None else str(t["value_num"]),
                        t["value_num"],
                        t["unit"],
                        t["flag"],
                    ),
                )
                loaded_counts["LAB_RESULT"] += 1
            except sqlite3.IntegrityError as err:
                rejected_counts["LAB_RESULT"] += 1
                logger.warning(f"LAB_RESULT for {rep_id} rejected: {err}")

    # 4. Integrate Pharmacy Dispensing from staged/dispensing_clean.xml
    xml_tree = ET.parse(CLEAN_XML_PATH)
    rx_link_stats = {"matched": 0, "orphan": 0, "ambiguous": 0}

    for disp in xml_tree.getroot().findall("dispense"):
        rx_id = disp.attrib["id"]
        disp_date = disp.attrib["date"]
        pat_el = disp.find("patient")
        _, pid_int = normalise_patient_id(pat_el.attrib["id"])
        total_amt = float(disp.find("total").text)
        items = disp.findall("./items/item")

        status, visit_id = match_visit_by_date_proximity(patient_visits_map.get(pid_int, []), disp_date)
        rx_link_stats[status] += 1

        if visit_id is None:
            rejected_counts["PRESCRIPTION"] += 1
            rejected_counts["RX_ITEM"] += len(items)
            logger.info(f"PRESCRIPTION {rx_id} (patient {pid_int}): ORPHAN — skipped from DB load")
            continue

        try:
            cur.execute(
                "INSERT INTO PRESCRIPTION (rx_id, visit_id, dispensed_on, total_amount) VALUES (?, ?, ?, ?)",
                (rx_id, visit_id, disp_date, total_amt),
            )
            loaded_counts["PRESCRIPTION"] += 1
        except sqlite3.IntegrityError as err:
            rejected_counts["PRESCRIPTION"] += 1
            logger.warning(f"PRESCRIPTION {rx_id} rejected: {err}")
            continue

        for item in items:
            try:
                cur.execute(
                    "INSERT INTO RX_ITEM (rx_id, drug_code, quantity, unit_price) VALUES (?, ?, ?, ?)",
                    (rx_id, item.attrib["drug_code"], int(item.attrib["qty"]), float(item.attrib["unit_price"])),
                )
                loaded_counts["RX_ITEM"] += 1
            except sqlite3.IntegrityError as err:
                rejected_counts["RX_ITEM"] += 1
                logger.warning(f"RX_ITEM {rx_id}/{item.attrib['drug_code']} rejected: {err}")

    conn.commit()
    conn.close()

    visit_link_stats = {"matched": len(visits), "orphan": 0, "ambiguous": 0}
    return {
        "id_normalization": id_stats,
        "integration_stats": {
            "Source A (Visits)": visit_link_stats,
            "Source B (Lab Reports)": lab_link_stats,
            "Source C (Prescriptions)": rx_link_stats,
        },
        "loaded_counts": dict(loaded_counts),
        "rejected_counts": dict(rejected_counts),
    }


if __name__ == "__main__":
    res = run_integration()
    print("=== Integration & Database Load Report ===")
    print("ID Normalization Stats :", res["id_normalization"])
    print("\n--- Integration Linkage (Matched / Orphan / Ambiguous) ---")
    for src, st in res["integration_stats"].items():
        print(f"  {src:<26}: {st}")
    print("\n--- SQLite Rows Loaded & Rejected per Table ---")
    tables = ["DEPARTMENT", "DOCTOR", "PATIENT", "VISIT", "LAB_REPORT", "LAB_RESULT", "PRESCRIPTION", "RX_ITEM"]
    for t in tables:
        print(f"  {t:<14}: loaded={res['loaded_counts'].get(t, 0):<4} | rejected={res['rejected_counts'].get(t, 0)}")
