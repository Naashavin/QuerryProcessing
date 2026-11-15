import importlib
import sys
from pathlib import Path
from config import RAW_DIR, STAGED_DIR, CURATED_DIR, LOGS_DIR, SEED_CSV_PATH


SEED_CSV_CONTENT = """patient_id,full_name,gender,dob,phone,visit_date,department,fee_paid
P1001,"Ravi Kumar",M,14/03/1985,9840012345,2026-10-03,Cardiology,"1,200.50"
P1002,Anitha S,Female,1990-07-21,,03-10-2026,ENT,850
P1003,"Mohammed, Irfan",m,05/11/1978,98400 56789,2026-10-04,Orthopaedics,₹ 1500
P1001,Ravi Kumar,M,14/03/1985,9840012345,2026-10-03,Cardiology,"1,200.50"
P1005,,F,31-12-1999,9791123456,2026/10/05,Paediatrics,600
P1006,Karthik R,Male,,9444098765,05-Oct-2026,General Medicine,NA
"""


def create_folders():
    """Create raw, staged, curated, and logs folders using pathlib."""
    for folder in (RAW_DIR, STAGED_DIR, CURATED_DIR, LOGS_DIR):
        Path(folder).mkdir(parents=True, exist_ok=True)
        print(f"[OK] Directory ready: {folder}")

    if not SEED_CSV_PATH.exists():
        SEED_CSV_PATH.write_text(SEED_CSV_CONTENT.strip() + "\n", encoding="utf-8")
        print(f"[OK] Seed sample created: {SEED_CSV_PATH}")


def environment_check():
    """Verify Python version and standard library modules."""
    print(f"\nPython Version: {sys.version.splitlines()[0]}")
    modules = [
        "csv",
        "json",
        "xml.etree.ElementTree",
        "sqlite3",
        "datetime",
        "re",
        "logging",
        "unittest",
    ]
    for mod in modules:
        importlib.import_module(mod)
        print(f"  [PASS] Imported {mod}")


if __name__ == "__main__":
    create_folders()
    environment_check()

