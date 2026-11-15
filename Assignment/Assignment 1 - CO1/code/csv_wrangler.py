import csv
import logging
from collections import Counter, defaultdict
from config import (
    CANONICAL_VISIT_COLUMNS,
    CLEAN_CSV_PATH,
    LOGS_DIR,
    RAW_CSV_PATH,
    REJECTED_CSV_PATH,
)
from utils import (
    clean_phone,
    normalise_gender,
    normalise_patient_id,
    parse_amount,
    parse_date,
    standardise_name,
)


def setup_logger():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "csv_wrangler.log"
    logger = logging.getLogger("csv_wrangler")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    return logger


def wrangle_csv(raw_path=RAW_CSV_PATH, clean_path=CLEAN_CSV_PATH, rejected_path=REJECTED_CSV_PATH):
    logger = setup_logger()
    raw_rows = []
    blank_lines = 0

    with open(raw_path, mode="r", encoding="utf-8-sig", newline="") as f:
        # Count blank lines separately while reading with DictReader
        lines = f.readlines()

    non_blank_lines = []
    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            blank_lines += 1
            logger.info(f"Skipped blank line at raw line {idx}")
        else:
            non_blank_lines.append(line)

    reader = csv.DictReader(non_blank_lines)
    columns = reader.fieldnames or []
    raw_rows = list(reader)

    # Initial analysis
    raw_unique_patients = set()
    missing_counts = Counter()
    dept_counts = Counter()
    for r in raw_rows:
        if None in r or any(r.get(c) is None for c in columns):
            continue
        raw_unique_patients.add((r.get("patient_id") or "").strip())
        dept_counts[(r.get("department") or "").strip()] += 1
        for c in columns:
            val = (r.get(c) or "").strip()
            if val == "" or val.upper() == "NA":
                missing_counts[c] += 1

    clean_rows = []
    rejected_rows = []
    seen_keys = set()
    duplicates_removed = 0

    for row_num, r in enumerate(raw_rows, start=2):
        # Detect wrong number of columns (extra fields stored under key None, or missing columns = None)
        if None in r or any(r.get(c) is None for c in columns):
            rec = {c: r.get(c, "") for c in columns}
            rec["rejection_reason"] = "MALFORMED_ROW_COLUMNS"
            rejected_rows.append(rec)
            logger.warning(f"Row {row_num}: rejected MALFORMED_ROW_COLUMNS")
            continue

        pid_str, _ = normalise_patient_id(r.get("patient_id"))
        full_name = standardise_name(r.get("full_name"))
        gender = normalise_gender(r.get("gender"))
        dob = parse_date(r.get("dob"))
        phone = clean_phone(r.get("phone"))
        visit_date = parse_date(r.get("visit_date"))
        department = standardise_name(r.get("department"))
        if department and department.upper() == "ENT":
            department = "ENT"
        raw_fee_str = (r.get("fee_paid") or "").strip()
        fee_is_missing = raw_fee_str == "" or raw_fee_str.upper() in ("NA", "N/A", "NULL")
        fee_paid = 0.0 if fee_is_missing else parse_amount(raw_fee_str)

        reason = None
        if not pid_str:
            reason = "INVALID_PATIENT_ID"
        elif not full_name:
            reason = "MISSING_NAME"
        elif not gender:
            reason = "INVALID_GENDER"
        elif not visit_date:
            reason = "INVALID_VISIT_DATE"
        elif not department:
            reason = "MISSING_DEPARTMENT"
        elif fee_paid is None:
            reason = "INVALID_FEE"

        if reason:
            rec = dict(r)
            rec["rejection_reason"] = reason
            rejected_rows.append(rec)
            logger.warning(f"Row {row_num} ({r.get('patient_id')}): rejected {reason}")
            continue

        dedup_key = (pid_str, visit_date, department)
        if dedup_key in seen_keys:
            duplicates_removed += 1
            logger.info(f"Row {row_num}: removed duplicate visit {dedup_key}")
            continue
        seen_keys.add(dedup_key)

        clean_rows.append({
            "patient_id": pid_str,
            "full_name": full_name,
            "gender": gender,
            "dob": dob if dob else "",
            "phone": phone if phone else "",
            "visit_date": visit_date,
            "department": department,
            "fee_paid": f"{fee_paid:.2f}",
            "dob_missing": str(dob is None),
            "phone_missing": str(phone is None),
            "fee_missing": str(fee_is_missing),
        })

    clean_path.parent.mkdir(parents=True, exist_ok=True)
    with open(clean_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CANONICAL_VISIT_COLUMNS)
        writer.writeheader()
        writer.writerows(clean_rows)

    rej_fields = list(columns) + ["rejection_reason"]
    with open(rejected_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rej_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rejected_rows)

    # Fee summary per department using plain Python defaultdict
    dept_fees = defaultdict(float)
    for r in clean_rows:
        dept_fees[r["department"]] += float(r["fee_paid"])

    summary = {
        "input_rows": len(raw_rows),
        "blank_lines_skipped": blank_lines,
        "columns": columns,
        "raw_unique_patient_refs": len(raw_unique_patients),
        "missing_counts": dict(missing_counts),
        "top_departments": dept_counts.most_common(5),
        "clean_rows": len(clean_rows),
        "rejected_rows": len(rejected_rows),
        "duplicates_removed": duplicates_removed,
        "reconciled": len(raw_rows) == (len(clean_rows) + len(rejected_rows) + duplicates_removed),
        "dept_fees": {k: round(v, 2) for k, v in sorted(dept_fees.items())},
    }
    return summary


if __name__ == "__main__":
    res = wrangle_csv()
    print("=== CSV Wrangler Summary ===")
    print("Columns            :", res["columns"])
    print("Input data rows    :", res["input_rows"])
    print("Clean rows written :", res["clean_rows"])
    print("Rejected rows      :", res["rejected_rows"])
    print("Duplicates removed :", res["duplicates_removed"])
    print(f"Reconciliation     : {res['input_rows']} == {res['clean_rows']} + {res['rejected_rows']} + {res['duplicates_removed']} -> {res['reconciled']}")
    print("Top Departments    :", res["top_departments"])
    print("\n--- Total Fee Collected Per Department (INR) ---")
    for dept, total in res["dept_fees"].items():
        print(f"  {dept:<18}: Rs. {total:,.2f}")
