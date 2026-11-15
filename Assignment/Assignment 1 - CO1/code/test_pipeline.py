import csv
import json
import sqlite3
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from convert import round_trip_test
from csv_wrangler import wrangle_csv
from json_lines_wrangler import wrangle_jsonl_streaming
from json_wrangler import wrangle_json
from schema import DDL_STATEMENTS
from utils import (
    clean_phone,
    normalise_gender,
    normalise_patient_id,
    parse_amount,
    parse_date,
    parse_eu_amount,
    standardise_name,
    utc_to_ist,
)
from xml_wrangler import wrangle_xml


class TestCityCarePipeline(unittest.TestCase):
    # --- Unit Tests on Utility Functions (6 tests) ---
    def test_01_normalise_gender(self):
        self.assertEqual(normalise_gender("Male"), "M")
        self.assertEqual(normalise_gender("female"), "F")
        self.assertIsNone(normalise_gender("xyz"))

    def test_02_parse_date_mixed_formats(self):
        self.assertEqual(parse_date("03-10-2026"), "2026-10-03")
        self.assertEqual(parse_date("05-Oct-2026"), "2026-10-05")
        self.assertEqual(parse_date("04.10.2026"), "2026-10-04")
        self.assertIsNone(parse_date("99/99/2026"))

    def test_03_clean_phone(self):
        self.assertEqual(clean_phone("98400 56789"), "9840056789")
        self.assertEqual(clean_phone("+91-9444098765"), "9444098765")
        self.assertIsNone(clean_phone("12345"))

    def test_04_parse_amount_and_eu_amount(self):
        self.assertEqual(parse_amount("1,200.50"), 1200.50)
        self.assertEqual(parse_amount("₹ 1500"), 1500.00)
        self.assertIsNone(parse_amount("NA"))
        self.assertEqual(parse_eu_amount("1.250,00 INR"), 1250.00)

    def test_05_standardise_name(self):
        self.assertEqual(standardise_name("Mohammed, Irfan"), "Mohammed Irfan")
        self.assertEqual(standardise_name("  karthik   r "), "Karthik R")
        self.assertIsNone(standardise_name(""))

    def test_06_normalise_patient_id_and_utc_to_ist(self):
        self.assertEqual(normalise_patient_id("PT-01001"), ("P1001", 1001))
        self.assertEqual(normalise_patient_id("1001"), ("P1001", 1001))
        ist_iso, ist_date = utc_to_ist("2026-11-09T14:30:00Z")
        self.assertEqual(ist_date, "2026-11-09")
        self.assertIn("20:00:00+05:30", ist_iso)

    # --- Format Tests (CSV, JSON, XML, JSONL) (4 tests) ---
    def test_07_csv_wrangler_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            raw_csv = tdir / "raw.csv"
            raw_csv.write_text(
                'patient_id,full_name,gender,dob,phone,visit_date,department,fee_paid\n'
                'P1001,"Ravi Kumar",M,14/03/1985,9840012345,2026-10-03,Cardiology,"1,200.50"\n'
                '1001,"Ravi Kumar",Male,14/03/1985,9840012345,03-10-2026,Cardiology,"1,200.50"\n'
                'P1005,,F,31-12-1999,9791123456,2026/10/05,Paediatrics,600\n',
                encoding="utf-8",
            )
            res = wrangle_csv(raw_csv, tdir / "clean.csv", tdir / "rej.csv")
            self.assertTrue(res["reconciled"])
            self.assertEqual(res["clean_rows"], 1)
            self.assertEqual(res["duplicates_removed"], 1)
            self.assertEqual(res["rejected_rows"], 1)

    def test_08_json_wrangler_flattening(self):
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            raw_json = tdir / "labs.json"
            raw_json.write_text(
                json.dumps([
                    {
                        "lab_report_id": "LR-1",
                        "patient_ref": "1001",
                        "collected_at": "2026-10-03T09:42:00+05:30",
                        "tests": [{"code": "HB", "value": "13.2", "unit": "g/dL", "ref_range": {"low": 13.0, "high": 17.0}}],
                    },
                    {
                        "lab_report_id": "LR-2",
                        "patient_ref": "P1002",
                        "collected_at": "2026-10-03T11:05:00+05:30",
                        "tests": [{"code": "TSH", "value": "pending", "unit": "mIU/L", "ref_range": None}],
                    },
                ]),
                encoding="utf-8",
            )
            res = wrangle_json(raw_json, tdir / "flat.json", tdir / "exc.json")
            self.assertEqual(res["flattened_tests"], 2)
            self.assertEqual(res["exceptions_count"], 0)

    def test_09_xml_wrangler_total_recomputation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            raw_xml = tdir / "rx.xml"
            raw_xml.write_text(
                '<pharmacy_dispensing branch="Hospital-B">'
                '<dispense id="RX-1" date="04.10.2026">'
                '<patient id="1003" name="Mohammed Irfan"/>'
                '<items><item drug_code="AMX500" qty="10" unit_price="5.00">Amox</item></items>'
                '<total currency="INR">99.00</total>'
                '</dispense></pharmacy_dispensing>',
                encoding="utf-8",
            )
            res = wrangle_xml(raw_xml, tdir / "clean.xml", tdir / "items.csv", tdir / "none.xml")
            self.assertEqual(res["mismatch_count"], 1)
            self.assertEqual(res["largest_discrepancy"], 49.00)

    def test_10_jsonl_streaming_wrangler(self):
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            raw_jl = tdir / "tele.jsonl"
            raw_jl.write_text(
                '{"session_id":"TM-1","patient":{"national_id":"PT-000123","legacy_id":"P1001","name":{"first":"Anitha","last":"S"}},"start_time":"2026-11-09T14:30:00Z","duration_min":"18","consultation_fee":"1.250,00 INR","doctor":{"doctor_id":"D-31","speciality":"ENT"},"prescribed":[]}\n'
                '{MALFORMED LINE\n',
                encoding="utf-8",
            )
            res = wrangle_jsonl_streaming(raw_jl, tdir / "tc.csv", tdir / "tr.csv")
            self.assertEqual(res["clean_count"], 1)
            self.assertEqual(res["rejected_count"], 1)

    # --- Integration & End-to-End Tests (3 tests) ---
    def test_11_sqlite_foreign_key_enforcement(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(DDL_STATEMENTS)
        conn.execute("INSERT INTO DEPARTMENT VALUES (1, 'Cardiology')")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO DOCTOR VALUES ('D-1', 'Dr. Test', 999)")
        conn.close()

    def test_12_round_trip_csv_json_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            src = tdir / "src.csv"
            dst = tdir / "dst.csv"
            src.write_text("visit_id,patient_id,fee_amount\n1,1001,1200.5\n2,1002,850.0\n", encoding="utf-8")
            rt = round_trip_test(src, dst)
            self.assertTrue(rt["content_identical"])

    def test_13_end_to_end_pipeline_outputs_exist(self):
        from config import CLEAN_CSV_PATH, DB_PATH, LAB_FLAT_JSON_PATH, CLEAN_XML_PATH
        self.assertTrue(CLEAN_CSV_PATH.exists())
        self.assertTrue(LAB_FLAT_JSON_PATH.exists())
        self.assertTrue(CLEAN_XML_PATH.exists())
        self.assertTrue(DB_PATH.exists())

    # --- Negative / Hostile Input Tests (3 tests) ---
    def test_14_negative_malformed_json_raises(self):
        with self.assertRaises(json.JSONDecodeError):
            json.loads('{"id": "1",}')

    def test_15_negative_malformed_xml_raises(self):
        with self.assertRaises(ET.ParseError):
            ET.fromstring("<root><item></root>")

    def test_16_negative_check_constraint_invalid_gender(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(DDL_STATEMENTS)
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO PATIENT VALUES (1001, 'Test', 'Z', NULL, NULL, '2026-10-01')")
        conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)

