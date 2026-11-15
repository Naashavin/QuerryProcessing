import argparse
import csv
import json
import random
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from config import INJECTION_LOG_PATH, RAW_DIR


DEPARTMENTS = [
    ("Cardiology", "Dr. S. Meena", "D-17"),
    ("ENT", "Dr. R. Karthik", "D-31"),
    ("Orthopaedics", "Dr. V. Rajesh", "D-22"),
    ("Paediatrics", "Dr. P. Lakshmi", "D-09"),
    ("General Medicine", "Dr. A. Suresh", "D-14"),
]

FIRST_NAMES = [
    "Ravi", "Anitha", "Mohammed", "Karthik", "Priya", "Suresh", "Divya",
    "Arjun", "Kavitha", "Vikram", "Sneha", "Deepak", "Nandhini", "Rahul",
    "Meena", "Prakash", "Lakshmi", "Harish", "Swathi", "Ganesh",
]
LAST_NAMES = ["Kumar", "S", "Irfan", "R", "N", "Nair", "Reddy", "Sharma", "Menon", "Babu"]

TESTS_CATALOG = [
    ("HB", "Haemoglobin", "g/dL", 13.0, 17.0),
    ("GLU-F", "Fasting Glucose", "mg/dL", 70.0, 100.0),
    ("TSH", "Thyroid Stimulating Hormone", "mIU/L", 0.4, 4.0),
    ("WBC", "White Blood Cells", "10^3/uL", 4.0, 11.0),
    ("CREAT", "Serum Creatinine", "mg/dL", 0.6, 1.3),
]

DRUGS_CATALOG = [
    ("AMX500", "Amoxicillin 500mg", 4.50),
    ("PCM650", "Paracetamol 650mg", 2.25),
    ("CTZ10", "Cetirizine 10mg", 3.00),
    ("OMP20", "Omeprazole 20mg", 5.50),
    ("AZM500", "Azithromycin 500mg", 18.00),
]


def format_pid_style(pid_num, rng):
    style = rng.choice(["P", "NUM", "PT"])
    if style == "P":
        return f"P{pid_num}"
    if style == "NUM":
        return str(pid_num)
    return f"PT-{pid_num}"


def format_mixed_date(dt, rng):
    choice = rng.choice(["ISO", "DMY_SLASH", "DMY_DASH", "YMD_SLASH", "DMY_MON"])
    if choice == "ISO":
        return dt.strftime("%Y-%m-%d")
    if choice == "DMY_SLASH":
        return dt.strftime("%d/%m/%Y")
    if choice == "DMY_DASH":
        return dt.strftime("%d-%m-%Y")
    if choice == "YMD_SLASH":
        return dt.strftime("%Y/%m/%d")
    return dt.strftime("%d-%b-%Y")


def generate_source_a(out_dir, rng, base_patient_nums):
    """Generate Source A CSV with >=200 rows, >=150 unique patients, and documented defects."""
    path = out_dir / "opd_visits.csv"
    stats = {"target_rows": 220, "duplicates": 0, "missing_phone": 0, "missing_dob": 0, "missing_fee": 0, "malformed": 0}
    rows = []
    patient_visit_dates = {}
    start_dt = datetime(2026, 10, 1)

    # First ensure all 165 base patients appear at least once (200 base rows total)
    pool_pids = list(base_patient_nums) + [rng.choice(base_patient_nums) for _ in range(35)]
    rng.shuffle(pool_pids)

    gender_choices = ["M", "F", "m", "f", "Male", "Female", "MALE", "female"]
    for idx, pid_num in enumerate(pool_pids):
        pid_str = format_pid_style(pid_num, rng)
        fn = rng.choice(FIRST_NAMES)
        ln = rng.choice(LAST_NAMES)
        if idx % 17 == 0:
            full_name = f"{fn}, {ln}"
        elif idx % 23 == 0:
            full_name = f"  {fn.lower()}   {ln.lower()} "
        else:
            full_name = f"{fn} {ln}"

        gender = rng.choice(gender_choices)
        dob_dt = datetime(rng.randint(1960, 2015), rng.randint(1, 12), rng.randint(1, 28))
        dob_str = format_mixed_date(dob_dt, rng)
        phone_str = f"{rng.choice([9, 8, 7])}{rng.randint(100000000, 999999999)}"
        if idx % 7 == 0:
            phone_str = f"{phone_str[:5]} {phone_str[5:]}"
        elif idx % 11 == 0:
            phone_str = f"+91-{phone_str}"

        visit_dt = start_dt + timedelta(days=rng.randint(0, 25))
        patient_visit_dates.setdefault(pid_num, []).append(visit_dt)
        visit_str = format_mixed_date(visit_dt, rng)
        dept = rng.choice(DEPARTMENTS)[0]

        fee_val = rng.choice([500, 600, 850, 1200.50, 1500, 2250])
        fee_style = rng.choice(["plain", "comma", "inr"])
        if fee_style == "comma" and fee_val >= 1000:
            fee_str = f"{fee_val:,.2f}"
        elif fee_style == "inr":
            fee_str = f"₹ {fee_val}"
        else:
            fee_str = str(fee_val)

        # Inject >=8% missing values in phone, dob, fee_paid (~10%)
        if rng.random() < 0.10:
            phone_str = ""
            stats["missing_phone"] += 1
        if rng.random() < 0.10:
            dob_str = ""
            stats["missing_dob"] += 1
        if rng.random() < 0.10:
            fee_str = rng.choice(["", "NA"])
            stats["missing_fee"] += 1

        rows.append([pid_str, full_name, gender, dob_str, phone_str, visit_str, dept, fee_str])

    # Inject >=5% duplicates (14 rows -> ~6.4%)
    for dup_row in rng.sample(rows, 14):
        rows.append(list(dup_row))
        stats["duplicates"] += 1

    # Inject 6 deliberately malformed rows
    malformed_rows = [
        ["P1005", "", "F", "31-12-1999", "9791123456", "2026/10/05", "Paediatrics", "600"],
        ["INVALID_ID", "Ghost Patient", "M", "1990-01-01", "9840011111", "2026-10-08", "ENT", "500"],
        ["P1010", "Bad Date Patient", "F", "1988-05-05", "9840022222", "99/99/2026", "Cardiology", "750"],
        ["P1011", "Neg Fee Patient", "M", "1982-09-12", "9840033333", "2026-10-12", "ENT", "-450"],
        ["P1012", "Extra Column Row", "M", "1980-02-14", "9840044444", "2026-10-14", "ENT", "400", "EXTRA_FIELD"],
        ["P1013", "Short Column Row", "F", "1995-03-10"],
    ]
    rows.extend(malformed_rows)
    stats["malformed"] = len(malformed_rows)
    stats["achieved_rows"] = len(rows)

    header = ["patient_id", "full_name", "gender", "dob", "phone", "visit_date", "department", "fee_paid"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    return path, stats, patient_visit_dates


def generate_source_b(out_dir, rng, base_patient_nums, patient_visit_dates):
    """Generate Source B JSON with >=100 lab reports, >=2 tests avg, >=60% linked + orphans + defects."""
    path = out_dir / "lab_reports.json"
    reports = []
    stats = {"total_reports": 110, "linked_patients": 0, "orphan_patients": 0, "malformed": 0, "total_tests": 0}
    start_dt = datetime(2026, 10, 1, 8, 30)

    for i in range(1, 111):
        report_id = f"LR-202610{(i % 25) + 1:02d}-{i:04d}"
        if i <= 75:
            pid_num = rng.choice(base_patient_nums)
            v_dt = rng.choice(patient_visit_dates[pid_num])
            collected_dt = v_dt + timedelta(days=rng.randint(0, 2), hours=rng.randint(8, 16), minutes=rng.randint(0, 59))
            stats["linked_patients"] += 1
        else:
            pid_num = 9000 + i
            collected_dt = start_dt + timedelta(days=rng.randint(0, 25), minutes=rng.randint(0, 480))
            stats["orphan_patients"] += 1

        patient_ref = format_pid_style(pid_num, rng)
        collected_str = collected_dt.strftime("%Y-%m-%dT%H:%M:00+05:30")

        dept, doc_name, doc_id = rng.choice(DEPARTMENTS)
        num_tests = rng.choice([2, 2, 3, 3])
        selected_tests = rng.sample(TESTS_CATALOG, num_tests)
        tests_list = []
        has_pending = False

        for code, tname, unit, low, high in selected_tests:
            r_val = rng.random()
            if r_val < 0.12:
                val = "pending"
                has_pending = True
            elif r_val < 0.40:
                # Numeric string
                val = str(round(rng.uniform(low * 0.7, high * 1.3), 2))
            else:
                val = round(rng.uniform(low * 0.7, high * 1.3), 2)

            ref_range = None if rng.random() < 0.15 else {"low": low, "high": high}
            tests_list.append({
                "code": code,
                "name": tname,
                "value": val,
                "unit": unit,
                "ref_range": ref_range,
            })

        report = {
            "lab_report_id": report_id,
            "patient_ref": patient_ref,
            "collected_at": collected_str,
            "tests": tests_list,
            "status": "IN_PROGRESS" if has_pending else "FINAL",
        }
        # Optional ordered_by block (absent in ~15% of reports)
        if rng.random() >= 0.15:
            report["ordered_by"] = {"doctor_id": doc_id, "name": doc_name, "department": dept}

        # Inject 6 deliberately malformed / unflattenable reports
        if i == 105:
            report["lab_report_id"] = ""
            stats["malformed"] += 1
        elif i == 106:
            report["patient_ref"] = "BAD_REF"
            stats["malformed"] += 1
        elif i == 107:
            report["collected_at"] = "invalid-timestamp"
            stats["malformed"] += 1
        elif i == 108:
            report["tests"] = []
            stats["malformed"] += 1
        elif i == 109:
            del report["tests"]
            stats["malformed"] += 1
        elif i == 110:
            report["tests"][0]["value"] = "ERR_SENSOR"
            stats["malformed"] += 1

        stats["total_tests"] += len(report.get("tests", []))
        reports.append(report)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)

    return path, stats


def generate_source_c(out_dir, rng, base_patient_nums, patient_visit_dates):
    """Generate Source C XML with >=100 dispensing records, 1-5 items, >=60% linked + orphans + defects."""
    path = out_dir / "pharmacy_dispensing.xml"
    root = ET.Element("pharmacy_dispensing", branch="Hospital-B")
    stats = {"total_dispenses": 110, "linked_patients": 0, "orphan_patients": 0, "malformed": 0}
    start_dt = datetime(2026, 10, 1)

    for i in range(1, 111):
        disp_id = f"RX-{88100 + i}"
        if i <= 75:
            pid_num = rng.choice(base_patient_nums)
            v_dt = rng.choice(patient_visit_dates[pid_num])
            disp_dt = v_dt + timedelta(days=rng.randint(0, 2))
            stats["linked_patients"] += 1
        else:
            pid_num = 9500 + i
            disp_dt = start_dt + timedelta(days=rng.randint(0, 25))
            stats["orphan_patients"] += 1

        date_str = disp_dt.strftime("%d.%m.%Y") if i % 2 == 0 else disp_dt.strftime("%Y-%m-%d")
        disp_el = ET.SubElement(root, "dispense", id=disp_id, date=date_str)

        pid_str = format_pid_style(pid_num, rng)
        pname = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        ET.SubElement(disp_el, "patient", id=pid_str, name=pname)
        items_el = ET.SubElement(disp_el, "items")

        # 5 deliberately malformed records
        if i == 106:
            # Empty items block
            stats["malformed"] += 1
            ET.SubElement(disp_el, "total", currency="INR").text = "50.00"
            continue

        chosen = rng.sample(DRUGS_CATALOG, rng.randint(1, 5))
        total_calc = 0.0
        for idx_d, (dcode, dname, uprice) in enumerate(chosen):
            qty = rng.randint(5, 20)
            if i == 107 and idx_d == 0:
                qty_str = "two"
                stats["malformed"] += 1
            elif i == 108 and idx_d == 0:
                qty_str = "N/A"
                stats["malformed"] += 1
            else:
                qty_str = str(qty)
                total_calc += qty * uprice

            item_el = ET.SubElement(items_el, "item", drug_code=dcode, qty=qty_str, unit_price=f"{uprice:.2f}")
            item_el.text = dname

        if i == 109:
            # Missing <total>
            stats["malformed"] += 1
        elif i == 110 or i % 15 == 0:
            # Wrong <total> discrepancy
            ET.SubElement(disp_el, "total", currency="INR").text = f"{total_calc + 25.50:.2f}"
            if i == 110:
                stats["malformed"] += 1
        else:
            ET.SubElement(disp_el, "total", currency="INR").text = f"{total_calc:.2f}"

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)

    # Also write a deliberately malformed XML for Task 9 ET.ParseError demonstration
    malformed_path = out_dir / "malformed_sample.xml"
    malformed_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<pharmacy_dispensing>\n'
        '  <dispense id="RX-999" date="2026-10-05">\n'
        '    <patient id="1001" name="Test">\n'
        '  </dispense>\n'
        '</pharmacy_dispensing>\n',
        encoding="utf-8",
    )

    return path, stats


def generate_source_d(out_dir, rng, base_patient_nums):
    """Generate Day-4 Source D JSON Lines file (>=20,000 sessions + 100 malformed lines)."""
    path = out_dir / "telemedicine_sessions.jsonl"
    stats = {"valid_lines": 20000, "malformed_lines": 100, "null_fees": 0, "missing_doctors": 0, "null_legacy_ids": 0}
    start_dt = datetime(2026, 11, 9, 8, 0, 0)

    with open(path, "w", encoding="utf-8") as f:
        for i in range(1, 20001):
            sid = f"TM-2026-{i:06d}"
            nat_id = f"PT-{(i % 5000) + 1:06d}"
            if rng.random() < 0.15:
                legacy_id = None
                stats["null_legacy_ids"] += 1
            else:
                legacy_id = format_pid_style(rng.choice(base_patient_nums), rng)

            start_utc = (start_dt + timedelta(seconds=i * 3)).strftime("%Y-%m-%dT%H:%M:%SZ")
            duration = str(rng.randint(10, 45))

            if rng.random() < 0.06:
                fee = None
                stats["null_fees"] += 1
            else:
                amt = rng.choice([500.0, 850.0, 1250.0, 1500.5, 2100.0])
                # Format European decimal style: 1.250,00 INR
                int_part = int(amt)
                dec_part = int(round((amt - int_part) * 100))
                int_str = f"{int_part:,}".replace(",", ".")
                fee = f"{int_str},{dec_part:02d} INR"

            rec = {
                "session_id": sid,
                "patient": {
                    "national_id": nat_id,
                    "legacy_id": legacy_id,
                    "name": {"first": rng.choice(FIRST_NAMES), "last": rng.choice(LAST_NAMES)},
                },
                "start_time": start_utc,
                "duration_min": duration,
                "consultation_fee": fee,
                "prescribed": (
                    [{"drug": rng.choice(DRUGS_CATALOG)[1], "qty": None if rng.random() < 0.25 else rng.randint(5, 15)}]
                    if rng.random() < 0.7 else []
                ),
            }
            if rng.random() >= 0.06:
                dept, _, doc_id = rng.choice(DEPARTMENTS)
                rec["doctor"] = {"doctor_id": doc_id, "speciality": dept}
            else:
                stats["missing_doctors"] += 1

            f.write(json.dumps(rec) + "\n")

        # Append 100 malformed lines
        for m in range(1, 101):
            if m % 3 == 0:
                f.write('{"session_id": "BAD_JSON", "patient": \n')
            elif m % 3 == 1:
                f.write(json.dumps({"session_id": "", "patient": {"national_id": "BAD"}, "start_time": "bad-ts"}) + "\n")
            else:
                f.write("NOT A JSON LINE AT ALL\n")

    return path, stats


def main():
    parser = argparse.ArgumentParser(description="Generate dirty multi-format dataset for CityCare.")
    parser.add_argument("--out-dir", type=Path, default=RAW_DIR, help="Output folder for generated raw files")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    base_patient_nums = list(range(1001, 1166))  # 165 unique patients

    _, stats_a, patient_visit_dates = generate_source_a(out_dir, rng, base_patient_nums)
    _, stats_b = generate_source_b(out_dir, rng, base_patient_nums, patient_visit_dates)
    _, stats_c = generate_source_c(out_dir, rng, base_patient_nums, patient_visit_dates)
    _, stats_d = generate_source_d(out_dir, rng, base_patient_nums)

    log_data = {
        "seed": args.seed,
        "source_a": stats_a,
        "source_b": stats_b,
        "source_c": stats_c,
        "source_d": stats_d,
    }
    INJECTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INJECTION_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)

    print("Data generation complete (Seed =", args.seed, ")")
    print("Source A (CSV)   :", stats_a)
    print("Source B (JSON)  :", stats_b)
    print("Source C (XML)   :", stats_c)
    print("Source D (JSONL) :", stats_d)


if __name__ == "__main__":
    main()
