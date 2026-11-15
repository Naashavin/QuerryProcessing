import json
from collections import Counter, defaultdict
from config import LAB_EXCEPTIONS_JSON_PATH, LAB_FLAT_JSON_PATH, RAW_JSON_PATH
from utils import normalise_patient_id, parse_date


def inspect_structure(obj, prefix="", paths_types=None, path_counts=None):
    """Recursively traverse parsed JSON and record key paths, observed types, and counts."""
    if paths_types is None:
        paths_types = defaultdict(set)
    if path_counts is None:
        path_counts = Counter()

    if isinstance(obj, dict):
        for k, v in obj.items():
            full_path = f"{prefix}.{k}" if prefix else k
            paths_types[full_path].add(type(v).__name__)
            path_counts[full_path] += 1
            if isinstance(v, (dict, list)):
                inspect_structure(v, full_path, paths_types, path_counts)
    elif isinstance(obj, list):
        arr_path = f"{prefix}[]" if prefix else "[]"
        for item in obj:
            if isinstance(item, (dict, list)):
                inspect_structure(item, arr_path, paths_types, path_counts)
            else:
                paths_types[arr_path].add(type(item).__name__)
                path_counts[arr_path] += 1
    return paths_types, path_counts


def compute_flag(value_num, ref_range):
    if value_num is None or not isinstance(ref_range, dict):
        return "UNKNOWN"
    low = ref_range.get("low")
    high = ref_range.get("high")
    if low is None or high is None:
        return "UNKNOWN"
    if value_num < float(low):
        return "LOW"
    if value_num > float(high):
        return "HIGH"
    return "NORMAL"


def wrangle_json(raw_path=RAW_JSON_PATH, flat_path=LAB_FLAT_JSON_PATH, exc_path=LAB_EXCEPTIONS_JSON_PATH):
    # Demonstrate json.loads() on a single inline JSON string
    sample_str = '{"lab_report_id":"LR-DEMO-01","patient_ref":"1001","collected_at":"2026-10-03T09:42:00+05:30","tests":[]}'
    _demo_parsed = json.loads(sample_str)

    # Load full file with json.load()
    with open(raw_path, "r", encoding="utf-8") as f:
        reports = json.load(f)

    # Walk each report independently to identify always-present vs optional top-level keys
    paths_types = defaultdict(set)
    path_counts = Counter()
    for rep in reports:
        inspect_structure(rep, "", paths_types, path_counts)

    total_reports = len(reports)
    schema_inventory = []
    for p in sorted(paths_types.keys()):
        types_str = ", ".join(sorted(paths_types[p]))
        presence = "Always" if ("[]" not in p and path_counts[p] == total_reports) else "Optional / Nested"
        schema_inventory.append({"path": p, "types": types_str, "count": path_counts[p], "presence": presence})

    flat_rows = []
    exceptions = []

    for idx, rep in enumerate(reports):
        report_id = (rep.get("lab_report_id") or "").strip()
        pid_str, _ = normalise_patient_id(rep.get("patient_ref"))
        collected_date = parse_date(rep.get("collected_at"))
        tests = rep.get("tests")

        if not report_id:
            exceptions.append({"index": idx, "record": rep, "reason": "MISSING_REPORT_ID"})
            continue
        if not pid_str:
            exceptions.append({"report_id": report_id, "record": rep, "reason": "INVALID_PATIENT_REF"})
            continue
        if not collected_date:
            exceptions.append({"report_id": report_id, "record": rep, "reason": "INVALID_COLLECTED_AT"})
            continue
        if not isinstance(tests, list) or len(tests) == 0:
            exceptions.append({"report_id": report_id, "record": rep, "reason": "MISSING_OR_EMPTY_TESTS"})
            continue

        ordered_by = rep.get("ordered_by") or {}
        doctor_id = ordered_by.get("doctor_id", "UNKNOWN")
        doctor_name = ordered_by.get("name", "UNKNOWN")

        for t in tests:
            test_code = (t.get("code") or "").strip()
            raw_val = t.get("value")
            unit = t.get("unit") or ""
            ref_range = t.get("ref_range")

            if not test_code:
                exceptions.append({"report_id": report_id, "test": t, "reason": "MISSING_TEST_CODE"})
                continue

            value_num = None
            if isinstance(raw_val, (int, float)):
                value_num = float(raw_val)
            elif isinstance(raw_val, str):
                s = raw_val.strip().lower()
                if s in ("pending", "", "na", "null"):
                    value_num = None
                else:
                    try:
                        value_num = float(s)
                    except ValueError:
                        exceptions.append({
                            "report_id": report_id,
                            "patient_id": pid_str,
                            "test_code": test_code,
                            "raw_value": raw_val,
                            "reason": "NON_NUMERIC_NON_PENDING_VALUE",
                        })
                        continue

            flag = compute_flag(value_num, ref_range)
            flat_rows.append({
                "report_id": report_id,
                "patient_id": pid_str,
                "collected_date": collected_date,
                "doctor_id": doctor_id,
                "doctor_name": doctor_name,
                "test_code": test_code,
                "value_num": value_num,
                "unit": unit,
                "flag": flag,
            })

    flat_path.parent.mkdir(parents=True, exist_ok=True)
    with open(flat_path, "w", encoding="utf-8") as f:
        json.dump(flat_rows, f, indent=2, ensure_ascii=False)
    with open(exc_path, "w", encoding="utf-8") as f:
        json.dump(exceptions, f, indent=2, ensure_ascii=False)

    # Flag proportions per test code
    flag_counts = defaultdict(Counter)
    for row in flat_rows:
        flag_counts[row["test_code"]][row["flag"]] += 1

    flag_rates = {}
    for code, cnts in sorted(flag_counts.items()):
        total_c = sum(cnts.values())
        flag_rates[code] = {
            flg: f"{cnts[flg]} ({cnts[flg]/total_c*100:.1f}%)"
            for flg in ("LOW", "NORMAL", "HIGH", "UNKNOWN")
        }
        flag_rates[code]["TOTAL"] = total_c

    return {
        "demo_loaded_id": _demo_parsed["lab_report_id"],
        "total_reports": total_reports,
        "flattened_tests": len(flat_rows),
        "exceptions_count": len(exceptions),
        "schema_inventory": schema_inventory,
        "flag_rates": flag_rates,
    }


if __name__ == "__main__":
    res = wrangle_json()
    print("=== JSON Wrangler Summary ===")
    print("json.loads demo report_id :", res["demo_loaded_id"])
    print("Total reports loaded      :", res["total_reports"])
    print("Flattened test rows       :", res["flattened_tests"])
    print("Exceptions logged         :", res["exceptions_count"])
    print("\n--- Recursive Key-Path Inventory ---")
    for item in res["schema_inventory"]:
        print(f"  {item['path']:<28} | {item['types']:<18} | count={item['count']:<3} | {item['presence']}")
    print("\n--- Flag Proportions per Test Code ---")
    for code, stats in res["flag_rates"].items():
        print(f"  {code:<6}: {stats}")

