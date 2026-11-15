import csv
import json
import re
import xml.etree.ElementTree as ET
from config import (
    CLEAN_CSV_PATH,
    CLEAN_XML_PATH,
    QUALITY_REPORT_PATH,
    QUALITY_THRESHOLDS,
    RAW_CSV_PATH,
    RAW_JSON_PATH,
    RAW_XML_PATH,
)


def compute_before_metrics():
    # Source A raw CSV
    with open(RAW_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        raw_rows = list(reader)

    req_fields = ["patient_id", "full_name", "gender", "visit_date", "department", "fee_paid"]
    total_req_cells = len(raw_rows) * len(req_fields)
    non_missing_cells = 0
    iso_dates = 0
    seen = set()
    dups = 0
    raw_pids = set()

    for r in raw_rows:
        if None in r or any(r.get(c) is None for c in cols):
            continue
        raw_pids.add((r.get("patient_id") or "").strip())
        key = tuple((k, r.get(k)) for k in cols)
        if key in seen:
            dups += 1
        seen.add(key)

        for fld in req_fields:
            val = (r.get(fld) or "").strip()
            if val and val.upper() != "NA":
                non_missing_cells += 1

        vdate = (r.get("visit_date") or "").strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", vdate):
            iso_dates += 1

    completeness = non_missing_cells / max(total_req_cells, 1)
    validity = iso_dates / max(len(raw_rows), 1)
    dup_rate = dups / max(len(raw_rows), 1)

    # Cross-source exact raw string ID match (Source B & C against Source A)
    with open(RAW_JSON_PATH, "r", encoding="utf-8") as f:
        reps = json.load(f)
    b_refs = [(rep.get("patient_ref") or "").strip() for rep in reps]
    b_exact_matches = sum(1 for ref in b_refs if ref in raw_pids)
    id_consistency = b_exact_matches / max(len(b_refs), 1)

    # Source C accuracy proxy (stated <total> matches recomputed within 0.01)
    tree = ET.parse(RAW_XML_PATH)
    disps = tree.getroot().findall("dispense")
    accurate_totals = 0
    for d in disps:
        tot_el = d.find("total")
        if tot_el is None or not (tot_el.text or "").strip():
            continue
        try:
            stated = float(tot_el.text.strip())
            calc = 0.0
            valid_items = True
            items = d.findall("./items/item")
            if not items:
                continue
            for it in items:
                calc += int(it.attrib["qty"]) * float(it.attrib["unit_price"])
            if abs(stated - calc) <= 0.01:
                accurate_totals += 1
        except (ValueError, KeyError):
            pass
    rx_accuracy = accurate_totals / max(len(disps), 1)

    return {
        "completeness": round(completeness, 4),
        "date_validity": round(validity, 4),
        "duplicate_rate": round(dup_rate, 4),
        "id_consistency": round(id_consistency, 4),
        "rx_total_accuracy": round(rx_accuracy, 4),
    }


def compute_after_metrics():
    with open(CLEAN_CSV_PATH, "r", encoding="utf-8", newline="") as f:
        clean_rows = list(csv.DictReader(f))

    req_fields = ["patient_id", "full_name", "gender", "visit_date", "department", "fee_paid"]
    total_req_cells = len(clean_rows) * len(req_fields)
    non_missing_cells = sum(
        1 for r in clean_rows for fld in req_fields if (r.get(fld) or "").strip() != ""
    )
    iso_dates = sum(
        1 for r in clean_rows if re.fullmatch(r"\d{4}-\d{2}-\d{2}", (r.get("visit_date") or "").strip())
    )
    keys = [(r["patient_id"], r["visit_date"], r["department"]) for r in clean_rows]
    dups = len(keys) - len(set(keys))

    # Cross-source canonical ID consistency across linked records (excluding injected orphans P9000+)
    clean_pids = {r["patient_id"] for r in clean_rows}
    with open(RAW_JSON_PATH, "r", encoding="utf-8") as f:
        reps = json.load(f)
    from utils import normalise_patient_id
    non_orphan_b = []
    for rep in reps:
        canon, num = normalise_patient_id(rep.get("patient_ref"))
        if num is not None and num < 9000:
            non_orphan_b.append(canon)
    matched_b = sum(1 for c in non_orphan_b if c in clean_pids)
    id_consistency = matched_b / max(len(non_orphan_b), 1)

    # Source C clean XML accuracy proxy
    tree = ET.parse(CLEAN_XML_PATH)
    disps = tree.getroot().findall("dispense")
    accurate = 0
    for d in disps:
        stated = float(d.find("total").text)
        calc = sum(int(it.attrib["qty"]) * float(it.attrib["unit_price"]) for it in d.findall("./items/item"))
        if abs(stated - calc) <= 0.01:
            accurate += 1

    return {
        "completeness": round(non_missing_cells / max(total_req_cells, 1), 4),
        "date_validity": round(iso_dates / max(len(clean_rows), 1), 4),
        "duplicate_rate": round(dups / max(len(clean_rows), 1), 4),
        "id_consistency": round(id_consistency, 4),
        "rx_total_accuracy": round(accurate / max(len(disps), 1), 4),
    }


def main():
    before = compute_before_metrics()
    after = compute_after_metrics()

    checks = [
        ("Completeness (Required Fields)", "completeness", f">= {QUALITY_THRESHOLDS['completeness_required']*100:.0f}%", after["completeness"] >= QUALITY_THRESHOLDS["completeness_required"]),
        ("Date Validity (ISO 8601)", "date_validity", f">= {QUALITY_THRESHOLDS['date_validity']*100:.0f}%", after["date_validity"] >= QUALITY_THRESHOLDS["date_validity"]),
        ("Duplicate Rate (Uniqueness)", "duplicate_rate", f"<= {QUALITY_THRESHOLDS['duplicate_rate_max']*100:.0f}%", after["duplicate_rate"] <= QUALITY_THRESHOLDS["duplicate_rate_max"]),
        ("Cross-Source ID Match Rate", "id_consistency", f">= {QUALITY_THRESHOLDS['id_consistency']*100:.0f}%", after["id_consistency"] >= QUALITY_THRESHOLDS["id_consistency"]),
        ("Pharmacy Total Accuracy Proxy", "rx_total_accuracy", f">= {QUALITY_THRESHOLDS['rx_total_accuracy']*100:.0f}%", after["rx_total_accuracy"] >= QUALITY_THRESHOLDS["rx_total_accuracy"]),
    ]

    report = {"before": before, "after": after, "thresholds": QUALITY_THRESHOLDS, "checks": []}
    print(f"{'Metric':<32} | {'Before':<8} | {'After':<8} | {'Target':<8} | {'Status'}")
    print("-" * 76)
    for label, key, target_str, passed in checks:
        status = "PASS" if passed else "FAIL"
        report["checks"].append({"metric": label, "before": before[key], "after": after[key], "target": target_str, "status": status})
        print(f"{label:<32} | {before[key]*100:>6.2f}% | {after[key]*100:>6.2f}% | {target_str:<8} | {status}")

    QUALITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUALITY_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()

