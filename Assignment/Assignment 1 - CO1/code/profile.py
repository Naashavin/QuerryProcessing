import argparse
import csv
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from config import INJECTION_LOG_PATH, RAW_DIR


def profile_csv(path):
    missing = Counter()
    categoricals = defaultdict(Counter)
    rows_seen = []
    dup_count = 0

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        total = 0
        for row in reader:
            total += 1
            key = tuple((k, row.get(k)) for k in fields)
            if key in rows_seen:
                dup_count += 1
            rows_seen.append(key)
            for col in fields:
                val = (row.get(col) or "").strip() if isinstance(row.get(col), str) else ""
                if val == "" or val.upper() == "NA":
                    missing[col] += 1
                elif col in ("gender", "department"):
                    categoricals[col][val] += 1

    return {
        "record_count": total,
        "duplicate_rows": dup_count,
        "missing_per_field": dict(missing),
        "categorical_distinct": {k: dict(v) for k, v in categoricals.items()},
    }


def profile_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    missing = Counter()
    statuses = Counter()
    total_tests = 0
    for rep in data:
        if not rep.get("lab_report_id"):
            missing["lab_report_id"] += 1
        if "ordered_by" not in rep:
            missing["ordered_by"] += 1
        tests = rep.get("tests")
        if not tests:
            missing["tests"] += 1
        else:
            total_tests += len(tests)
            for t in tests:
                if t.get("ref_range") is None:
                    missing["tests[].ref_range"] += 1
        statuses[rep.get("status", "MISSING")] += 1

    return {
        "record_count": len(data),
        "total_tests": total_tests,
        "avg_tests_per_report": round(total_tests / max(len(data), 1), 2),
        "missing_per_field": dict(missing),
        "status_values": dict(statuses),
    }


def profile_xml(path):
    tree = ET.parse(path)
    root = tree.getroot()
    dispenses = root.findall("dispense")
    missing = Counter()
    date_styles = Counter()
    total_items = 0

    for d in dispenses:
        dt = d.attrib.get("date", "")
        date_styles["DD.MM.YYYY" if "." in dt else "YYYY-MM-DD"] += 1
        if d.find("total") is None:
            missing["total_element"] += 1
        items = d.findall("./items/item")
        if not items:
            missing["empty_items"] += 1
        total_items += len(items)

    return {
        "record_count": len(dispenses),
        "total_items": total_items,
        "missing_per_field": dict(missing),
        "date_styles": dict(date_styles),
    }


def main():
    parser = argparse.ArgumentParser(description="Profile generated raw files and compare defect rates.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    args = parser.parse_args()

    prof_a = profile_csv(args.raw_dir / "opd_visits.csv")
    prof_b = profile_json(args.raw_dir / "lab_reports.json")
    prof_c = profile_xml(args.raw_dir / "pharmacy_dispensing.xml")

    print("=== Profiling Summary ===")
    print("Source A (CSV) :", prof_a)
    print("Source B (JSON):", prof_b)
    print("Source C (XML) :", prof_c)

    if INJECTION_LOG_PATH.exists():
        with open(INJECTION_LOG_PATH, "r", encoding="utf-8") as f:
            inj = json.load(f)
        print("\n=== Target vs Achieved Defect Comparison (Source A) ===")
        n_a = prof_a["record_count"]
        print(f"  Total Rows    : Target >=200  | Achieved = {n_a}")
        print(f"  Duplicates    : Target >=5.0% | Achieved = {prof_a['duplicate_rows']/n_a*100:.2f}% ({prof_a['duplicate_rows']})")
        for fld in ("phone", "dob", "fee_paid"):
            cnt = prof_a["missing_per_field"].get(fld, 0)
            print(f"  Missing {fld:<8}: Target >=8.0% | Achieved = {cnt/n_a*100:.2f}% ({cnt})")
        print(f"  Source B Linked Reports : {inj['source_b']['linked_patients']}/{prof_b['record_count']} ({inj['source_b']['linked_patients']/prof_b['record_count']*100:.1f}%)")
        print(f"  Source C Linked Dispenses: {inj['source_c']['linked_patients']}/{prof_c['record_count']} ({inj['source_c']['linked_patients']/prof_c['record_count']*100:.1f}%)")


if __name__ == "__main__":
    main()

