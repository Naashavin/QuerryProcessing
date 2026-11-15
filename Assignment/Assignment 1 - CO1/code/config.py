from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
STAGED_DIR = BASE_DIR / "staged"
CURATED_DIR = BASE_DIR / "curated"
LOGS_DIR = BASE_DIR / "logs"

# Source file paths
SEED_CSV_PATH = RAW_DIR / "seed_source_a.csv"
RAW_CSV_PATH = RAW_DIR / "opd_visits.csv"
RAW_JSON_PATH = RAW_DIR / "lab_reports.json"
RAW_XML_PATH = RAW_DIR / "pharmacy_dispensing.xml"
RAW_JSONL_PATH = RAW_DIR / "telemedicine_sessions.jsonl"
MALFORMED_XML_PATH = RAW_DIR / "malformed_sample.xml"

# Staged output paths
CLEAN_CSV_PATH = STAGED_DIR / "clean_visits.csv"
REJECTED_CSV_PATH = STAGED_DIR / "rejected_visits.csv"
LAB_FLAT_JSON_PATH = STAGED_DIR / "lab_results_flat.json"
LAB_EXCEPTIONS_JSON_PATH = STAGED_DIR / "lab_exceptions.json"
CLEAN_XML_PATH = STAGED_DIR / "dispensing_clean.xml"
DISPENSING_ITEMS_CSV_PATH = STAGED_DIR / "dispensing_items.csv"
TELE_CLEAN_CSV_PATH = STAGED_DIR / "tele_clean.csv"
TELE_REJECTED_CSV_PATH = STAGED_DIR / "tele_rejected.csv"

# Curated output paths
DB_PATH = CURATED_DIR / "citycare.db"
DB_V2_PATH = CURATED_DIR / "citycare_v2.db"
PATIENT_SUMMARY_JSON_PATH = CURATED_DIR / "patient_summary.json"
VISITS_FLAT_CSV_PATH = CURATED_DIR / "visits_flat.csv"
DISPENSING_REPORT_XML_PATH = CURATED_DIR / "dispensing_report.xml"
ROUNDTRIP_CSV_PATH = CURATED_DIR / "roundtrip_visits.csv"

# Logs & reports
INJECTION_LOG_PATH = LOGS_DIR / "injection_log.json"
QUALITY_REPORT_PATH = LOGS_DIR / "quality_report.json"

# Date formats supported in input data (Day-first for ambiguous numeric slash/dot/dash formats)
EXPECTED_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d-%b-%Y",
    "%d.%m.%Y",
]

CANONICAL_VISIT_COLUMNS = [
    "patient_id",
    "full_name",
    "gender",
    "dob",
    "phone",
    "visit_date",
    "department",
    "fee_paid",
    "dob_missing",
    "phone_missing",
    "fee_missing",
]

QUALITY_THRESHOLDS = {
    "date_validity": 0.98,
    "id_consistency": 0.95,
    "duplicate_rate_max": 0.01,
    "completeness_required": 0.98,
    "rx_total_accuracy": 0.99,
}
