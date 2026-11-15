import csv
import json
import sqlite3
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from config import (
    CURATED_DIR,
    DB_PATH,
    DISPENSING_REPORT_XML_PATH,
    PATIENT_SUMMARY_JSON_PATH,
    ROUNDTRIP_CSV_PATH,
    VISITS_FLAT_CSV_PATH,
)


def export_all(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # (a) patient_summary.json: nested Patient -> Visits -> Labs & Prescriptions
    patients = [dict(r) for r in cur.execute("SELECT * FROM PATIENT ORDER BY patient_id").fetchall()]
    summary = []

    for pat in patients:
        pid = pat["patient_id"]
        visits = [
            dict(v)
            for v in cur.execute(
                """
                SELECT v.visit_id, v.visit_date, v.fee_amount, d.doctor_name, dep.department_name
                FROM VISIT v
                JOIN DOCTOR d ON v.doctor_id = d.doctor_id
                JOIN DEPARTMENT dep ON v.department_id = dep.department_id
                WHERE v.patient_id = ?
                ORDER BY v.visit_date
                """,
                (pid,),
            ).fetchall()
        ]
        for v in visits:
            vid = v["visit_id"]
            labs = [
                dict(lr)
                for lr in cur.execute(
                    "SELECT report_id, collected_at, status FROM LAB_REPORT WHERE visit_id = ?",
                    (vid,),
                ).fetchall()
            ]
            for lb in labs:
                lb["results"] = [
                    dict(res)
                    for res in cur.execute(
                        "SELECT test_code, result_value, result_num, unit, flag FROM LAB_RESULT WHERE report_id = ?",
                        (lb["report_id"],),
                    ).fetchall()
                ]
            rxs = [
                dict(rx)
                for rx in cur.execute(
                    "SELECT rx_id, dispensed_on, total_amount FROM PRESCRIPTION WHERE visit_id = ?",
                    (vid,),
                ).fetchall()
            ]
            for rx in rxs:
                rx["items"] = [
                    dict(it)
                    for it in cur.execute(
                        "SELECT drug_code, quantity, unit_price FROM RX_ITEM WHERE rx_id = ?",
                        (rx["rx_id"],),
                    ).fetchall()
                ]
            v["lab_reports"] = labs
            v["prescriptions"] = rxs

        pat["visits"] = visits
        summary.append(pat)

    PATIENT_SUMMARY_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PATIENT_SUMMARY_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # (b) visits_flat.csv
    flat_visits = [
        dict(r)
        for r in cur.execute(
            """
            SELECT v.visit_id, p.patient_id, p.full_name, p.gender, p.date_of_birth,
                   p.phone, d.doctor_name, dep.department_name, v.visit_date, v.fee_amount
            FROM VISIT v
            JOIN PATIENT p ON v.patient_id = p.patient_id
            JOIN DOCTOR d ON v.doctor_id = d.doctor_id
            JOIN DEPARTMENT dep ON v.department_id = dep.department_id
            ORDER BY v.visit_id
            """
        ).fetchall()
    ]
    csv_cols = [
        "visit_id", "patient_id", "full_name", "gender", "date_of_birth",
        "phone", "doctor_name", "department_name", "visit_date", "fee_amount",
    ]
    with open(VISITS_FLAT_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_cols)
        writer.writeheader()
        for row in flat_visits:
            # Normalize None to empty string for clean CSV representation
            writer.writerow({k: ("" if row[k] is None else row[k]) for k in csv_cols})

    # (c) dispensing_report.xml
    disp_root = ET.Element("dispensing_report")
    rx_rows = cur.execute(
        """
        SELECT rx.rx_id, rx.visit_id, v.patient_id, p.full_name, rx.dispensed_on, rx.total_amount
        FROM PRESCRIPTION rx
        JOIN VISIT v ON rx.visit_id = v.visit_id
        JOIN PATIENT p ON v.patient_id = p.patient_id
        ORDER BY rx.rx_id
        """
    ).fetchall()

    for rx in rx_rows:
        rx_el = ET.SubElement(
            disp_root,
            "prescription",
            rx_id=rx["rx_id"],
            visit_id=str(rx["visit_id"]),
            dispensed_on=rx["dispensed_on"],
        )
        ET.SubElement(rx_el, "patient", id=str(rx["patient_id"]), name=rx["full_name"])
        items_el = ET.SubElement(rx_el, "items")
        for it in cur.execute(
            "SELECT drug_code, quantity, unit_price FROM RX_ITEM WHERE rx_id = ?",
            (rx["rx_id"],),
        ).fetchall():
            ET.SubElement(
                items_el,
                "item",
                drug_code=it["drug_code"],
                quantity=str(it["quantity"]),
                unit_price=f"{it['unit_price']:.2f}",
            )
        ET.SubElement(rx_el, "total_amount", currency="INR").text = f"{rx['total_amount']:.2f}"

    disp_tree = ET.ElementTree(disp_root)
    ET.indent(disp_tree, space="  ")
    disp_tree.write(DISPENSING_REPORT_XML_PATH, encoding="utf-8", xml_declaration=True)
    conn.close()
    return len(summary), len(flat_visits), len(rx_rows)


def round_trip_test(csv_in=VISITS_FLAT_CSV_PATH, csv_out=ROUNDTRIP_CSV_PATH):
    """Convert CSV -> JSON string -> CSV and verify exact content match."""
    with open(csv_in, "r", encoding="utf-8", newline="") as f:
        orig_reader = csv.DictReader(f)
        fieldnames = orig_reader.fieldnames
        orig_rows = list(orig_reader)

    # CSV -> JSON
    json_blob = json.dumps(orig_rows, ensure_ascii=False)
    # JSON -> CSV
    restored_rows = json.loads(json_blob)

    with open(csv_out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(restored_rows)

    with open(csv_out, "r", encoding="utf-8", newline="") as f:
        re_read_rows = list(csv.DictReader(f))

    identical = (orig_rows == re_read_rows)
    return {
        "rows_original": len(orig_rows),
        "rows_roundtrip": len(re_read_rows),
        "content_identical": identical,
    }


def benchmark_formats():
    """Compare file size and 5-run parse time on the SAME integrated visits dataset across CSV, JSON, XML."""
    with open(VISITS_FLAT_CSV_PATH, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    bench_json = CURATED_DIR / "_bench_visits.json"
    bench_xml = CURATED_DIR / "_bench_visits.xml"

    with open(bench_json, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    root = ET.Element("visits")
    for r in rows:
        el = ET.SubElement(root, "visit")
        for k, v in r.items():
            child = ET.SubElement(el, k)
            child.text = str(v)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(bench_xml, encoding="utf-8", xml_declaration=True)

    def time_parse(fn, runs=5):
        times = []
        for _ in range(runs):
            t0 = time.perf_counter()
            fn()
            times.append((time.perf_counter() - t0) * 1000.0)
        return round(sum(times) / len(times), 4)

    def read_csv():
        with open(VISITS_FLAT_CSV_PATH, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def read_json():
        with open(bench_json, encoding="utf-8") as fh:
            return json.load(fh)

    def read_xml():
        return ET.parse(bench_xml)

    csv_ms = time_parse(read_csv)
    json_ms = time_parse(read_json)
    xml_ms = time_parse(read_xml)

    results = [
        {"format": "CSV", "bytes": VISITS_FLAT_CSV_PATH.stat().st_size, "avg_parse_ms": csv_ms},
        {"format": "JSON", "bytes": bench_json.stat().st_size, "avg_parse_ms": json_ms},
        {"format": "XML", "bytes": bench_xml.stat().st_size, "avg_parse_ms": xml_ms},
    ]

    # Remove temporary benchmark copies (keep curated outputs clean)
    bench_json.unlink(missing_ok=True)
    bench_xml.unlink(missing_ok=True)
    return results


if __name__ == "__main__":
    n_pat, n_vis, n_rx = export_all()
    print(f"Exported: {n_pat} patients (JSON), {n_vis} visits (CSV), {n_rx} prescriptions (XML)")
    rt = round_trip_test()
    print("Round-trip CSV->JSON->CSV :", rt)
    print("\n--- Format Comparison (Same Integrated Visits Dataset, Avg of 5 Runs) ---")
    for r in benchmark_formats():
        print(f"  {r['format']:<5} | {r['bytes']:>7} bytes | avg parse = {r['avg_parse_ms']:.4f} ms")
