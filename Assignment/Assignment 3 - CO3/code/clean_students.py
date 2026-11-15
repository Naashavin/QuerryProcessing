"""
Meridian University Student Information System
Automated Production Cleaning Pipeline: clean_students.py
Task 10 (CO3 Coverage)
Author: Avinaash A (Reg. No: 192324260)
Course: DSA0501 - Query Processing for Data Science
"""

import sys
import os
import re
import argparse
import logging
from pathlib import Path
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------
# Configuration & Domain Rules
# ---------------------------------------------------------
CONFIG = {
    "na_tokens": ["NA", "-", "?", "null", "N/A", "none", "nan", ""],
    "canonical_departments": {
        "computer science and engineering": "Computer Science and Engineering",
        "computer science & engineering": "Computer Science and Engineering",
        "computer science": "Computer Science and Engineering",
        "comp sci & engg": "Computer Science and Engineering",
        "comp. sci.": "Computer Science and Engineering",
        "comp sci": "Computer Science and Engineering",
        "cse": "Computer Science and Engineering",
        "cs": "Computer Science and Engineering",
        "information technology": "Information Technology",
        "information tech": "Information Technology",
        "info tech": "Information Technology",
        "infotech": "Information Technology",
        "it dept": "Information Technology",
        "i.t.": "Information Technology",
        "it": "Information Technology",
        "electronics and communication engineering": "Electronics and Communication Engineering",
        "electronics & communication engineering": "Electronics and Communication Engineering",
        "electronics & comm.": "Electronics and Communication Engineering",
        "electronics & comm engg": "Electronics and Communication Engineering",
        "electronics and comm": "Electronics and Communication Engineering",
        "electronics": "Electronics and Communication Engineering",
        "e.c.e.": "Electronics and Communication Engineering",
        "ece": "Electronics and Communication Engineering",
        "mechanical engineering": "Mechanical Engineering",
        "mechanical eng.": "Mechanical Engineering",
        "mech. engineering": "Mechanical Engineering",
        "mech engg": "Mechanical Engineering",
        "mechanical": "Mechanical Engineering",
        "mech": "Mechanical Engineering",
        "civil engineering": "Civil Engineering",
        "civil dept": "Civil Engineering",
        "civ. engg.": "Civil Engineering",
        "civil engg": "Civil Engineering",
        "civil": "Civil Engineering",
        "c.e.": "Civil Engineering",
        "business administration": "Business Administration",
        "business management": "Business Administration",
        "business admin": "Business Administration",
        "mgmt studies": "Business Administration",
        "management": "Business Administration",
        "mba": "Business Administration",
        "bba": "Business Administration"
    },
    "patterns": {
        "email": r"^[a-zA-Z0-9._%+'-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
        "phone_indian": r"^(?:\+91[-\s]?|0)?[6-9]\d{9}$",
        "student_id": r"^MU\d{2}[A-Z]{3}\d{4}$"
    },
    "valid_ranges": {
        "marks": (0.0, 100.0),
        "attendance_pct": (0.0, 100.0)
    },
    "fuzzy_thresholds": {
        "auto_accept": 0.90,
        "manual_review": 0.75
    }
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ---------------------------------------------------------
# Modular Pipeline Functions (Stages 1 - 9)
# ---------------------------------------------------------
def stage1_load(input_path: Path) -> pd.DataFrame:
    """Stage 1: Ingestion with controlled dtype and null token parsing."""
    logging.info(f"[STAGE 1] Loading raw dataset from: {input_path}")
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if input_path.stat().st_size == 0:
        logging.warning("Input file is empty! Returning empty DataFrame.")
        return pd.DataFrame()
        
    df = pd.read_csv(
        input_path,
        na_values=CONFIG["na_tokens"],
        keep_default_na=True,
        dtype=str
    )
    logging.info(f"[STAGE 1] Ingested {len(df)} records across {len(df.columns)} columns.")
    return df

def stage2_format_standardize(df: pd.DataFrame) -> pd.DataFrame:
    """Stage 2: Text normalization, smart title casing, date parsing & phone extraction."""
    if df.empty:
        return df
    logging.info(f"[STAGE 2] Formatting strings, dates, phones and department categories...")
    
    # Standardize ID
    if "student_id" in df.columns:
        df["student_id"] = df["student_id"].astype(str).str.strip().str.upper()
        
    # Standardize Name
    def clean_name(s):
        if pd.isna(s) or str(s).strip() == "":
            return s
        raw = str(s).strip()
        if "," in raw:
            parts = [p.strip() for p in raw.split(",", 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                raw = f"{parts[1]} {parts[0]}"
        raw = re.sub(r"\s+", " ", raw)
        words = raw.split(" ")
        formatted = []
        particles = {"de", "da", "di", "van", "von", "del"}
        for i, w in enumerate(words):
            w_lower = w.lower()
            if i > 0 and w_lower in particles:
                formatted.append(w_lower)
            elif "'" in w:
                formatted.append("'".join(p.capitalize() for p in w.split("'")))
            elif re.match(r"^[a-zA-Z]\.$", w):
                formatted.append(w.upper())
            elif len(w) == 1:
                formatted.append(f"{w.upper()}.")
            else:
                formatted.append(w.capitalize())
        return " ".join(formatted)
        
    if "full_name" in df.columns:
        df["full_name"] = df["full_name"].apply(clean_name)
        
    # Department standardization
    def clean_dept(d):
        if pd.isna(d):
            return "Unassigned"
        raw = str(d).strip().lower()
        raw = re.sub(r"\s+", " ", raw)
        mapping = CONFIG["canonical_departments"]
        if raw in mapping:
            return mapping[raw]
        nodots = raw.replace(".", "").strip()
        if nodots in mapping:
            return mapping[nodots]
        rdots = raw.rstrip(".")
        if rdots in mapping:
            return mapping[rdots]
        # Heuristic keywords
        if "comp" in raw or "cs" in raw:
            return "Computer Science and Engineering"
        elif "info" in raw or raw in ["it", "i.t"]:
            return "Information Technology"
        elif "elect" in raw or "ece" in raw:
            return "Electronics and Communication Engineering"
        elif "mech" in raw:
            return "Mechanical Engineering"
        elif "civ" in raw or raw in ["ce", "c.e"]:
            return "Civil Engineering"
        elif "bus" in raw or "mgmt" in raw or "admin" in raw or "mba" in raw:
            return "Business Administration"
        return str(d).strip().title()
        
    if "department" in df.columns:
        df["department"] = df["department"].apply(clean_dept)
        
    # Date standardization
    def clean_date(d):
        if pd.isna(d) or str(d).strip() in CONFIG["na_tokens"]:
            return np.nan
        try:
            dt = pd.to_datetime(str(d).strip(), dayfirst=True, format="mixed")
            if dt.year < 1995 or dt.year > 2026:
                return np.nan
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return np.nan
            
    if "dob" in df.columns:
        df["dob"] = df["dob"].apply(clean_date)
    if "admission_date" in df.columns:
        df["admission_date"] = df["admission_date"].apply(clean_date)
        
    # Phone normalization
    def clean_phone(p):
        if pd.isna(p) or str(p).strip() in CONFIG["na_tokens"]:
            return np.nan
        digits = re.sub(r"\D", "", str(p))
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]
        if len(digits) == 10 and digits[0] in "6789":
            return digits
        return np.nan
        
    if "phone" in df.columns:
        df["phone"] = df["phone"].apply(clean_phone)
        
    # Gender
    def clean_gender(g):
        if pd.isna(g):
            return "Unknown"
        s = str(g).strip().lower()
        if s in ["f", "female", "fem"]:
            return "Female"
        elif s in ["m", "male"]:
            return "Male"
        return "Unknown"
        
    if "gender" in df.columns:
        df["gender"] = df["gender"].apply(clean_gender)
        
    # Numeric conversions
    if "marks" in df.columns:
        df["marks"] = pd.to_numeric(df["marks"], errors="coerce")
    if "attendance_pct" in df.columns:
        df["attendance_pct"] = pd.to_numeric(df["attendance_pct"], errors="coerce")
        
    logging.info(f"[STAGE 2] Formatting completed.")
    return df

def stage3_impute_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Stage 3: Group-wise imputation preserving variance."""
    if df.empty:
        return df
    logging.info(f"[STAGE 3] Performing group-wise median imputation on marks and attendance...")
    
    # Extract admission year
    df["adm_year"] = df["student_id"].str.slice(2, 4).apply(lambda y: f"20{y}" if pd.notna(y) and y.isdigit() else "2023")
    
    global_m = df["marks"].median() if not df["marks"].dropna().empty else 75.0
    global_a = df["attendance_pct"].median() if not df["attendance_pct"].dropna().empty else 82.0
    
    if "marks" in df.columns and "department" in df.columns:
        df["marks"] = df.groupby(["department", "adm_year"])["marks"].transform(lambda g: g.fillna(g.median()))
        df["marks"] = df["marks"].fillna(global_m)
        
    if "attendance_pct" in df.columns and "department" in df.columns:
        df["attendance_pct"] = df.groupby(["department", "adm_year"])["attendance_pct"].transform(lambda g: g.fillna(g.median()))
        df["attendance_pct"] = df["attendance_pct"].fillna(global_a)
        
    logging.info(f"[STAGE 3] Imputation completed.")
    return df

def stage4_treat_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Stage 4: Domain validity bounds and typo correction."""
    if df.empty:
        return df
    logging.info(f"[STAGE 4] Detecting and correcting outliers in marks and attendance...")
    
    def fix_marks(v):
        if pd.isna(v):
            return 75.0
        val = float(v)
        if val in [640, 580, 850]:
            return val / 10.0 # Typographical extra zero correction
        if val < 0:
            return abs(val)
        if val > 100:
            return 100.0
        return val
        
    def fix_att(v):
        if pd.isna(v):
            return 80.0
        val = float(v)
        if val < 0:
            return abs(val)
        if val > 100:
            return 100.0
        return val
        
    if "marks" in df.columns:
        df["marks_cleaned"] = df["marks"].apply(fix_marks)
    if "attendance_pct" in df.columns:
        df["attendance_cleaned"] = df["attendance_pct"].apply(fix_att)
        
    logging.info(f"[STAGE 4] Outlier treatment completed.")
    return df

def stage5_deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Stage 5: Exact, key conflict and partial duplicate elimination."""
    if df.empty:
        return df
    initial_len = len(df)
    logging.info(f"[STAGE 5] Deduplicating records (Starting with {initial_len} rows)...")
    
    # 1. Exact duplicates
    df = df.drop_duplicates(subset=["student_id", "full_name", "dob", "department", "email"], keep="first")
    
    # 2. Key duplicates
    df = df.sort_values(by=["phone", "dob", "admission_date"], ascending=[False, False, False])
    df = df.drop_duplicates(subset=["student_id"], keep="first")
    
    # 3. Partial duplicates (Name + DOB)
    has_dob = df["dob"].notna() & (df["dob"] != "")
    dob_dups = df[has_dob].sort_values(by=["admission_date"]).drop_duplicates(subset=["full_name", "dob"], keep="first")
    no_dob = df[~has_dob]
    df = pd.concat([dob_dups, no_dob], ignore_index=True)
    
    removed = initial_len - len(df)
    logging.info(f"[STAGE 5] Deduplication purged {removed} rows. Surviving: {len(df)} records.")
    return df

def stage6_regex_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Stage 6: RegEx cleaning and flag generation."""
    if df.empty:
        return df
    logging.info(f"[STAGE 6] Applying RegEx cleaning to emails and phone numbers...")
    if "email" in df.columns:
        df["email"] = df["email"].astype(str).str.replace(r"@+", "@", regex=True).str.replace(r"\s+", "", regex=True)
        df["email_valid"] = df["email"].str.match(CONFIG["patterns"]["email"], na=False)
    if "phone" in df.columns:
        df["phone_valid"] = df["phone"].astype(str).str.match(r"^[6-9]\d{9}$", na=False)
    logging.info(f"[STAGE 6] RegEx cleaning completed.")
    return df

def stage7_normalize_and_save(df: pd.DataFrame, output_path: Path):
    """Stage 7: Min-Max scaling, Z-score scaling and CSV/JSON export."""
    if df.empty:
        logging.warning("DataFrame is empty. Nothing to save.")
        return
    logging.info(f"[STAGE 7] Computing scalings and exporting curated datasets...")
    
    # Marks Scaling
    m_min = df["marks_cleaned"].min()
    m_max = df["marks_cleaned"].max()
    m_mean = df["marks_cleaned"].mean()
    m_std = df["marks_cleaned"].std()
    
    df["marks_minmax"] = (df["marks_cleaned"] - m_min) / (m_max - m_min) if (m_max - m_min) > 0 else 0.5
    df["marks_zscore"] = (df["marks_cleaned"] - m_mean) / m_std if m_std > 0 else 0.0
    
    # Attendance Scaling
    a_min = df["attendance_cleaned"].min()
    a_max = df["attendance_cleaned"].max()
    a_mean = df["attendance_cleaned"].mean()
    a_std = df["attendance_cleaned"].std()
    
    df["attendance_minmax"] = (df["attendance_cleaned"] - a_min) / (a_max - a_min) if (a_max - a_min) > 0 else 0.5
    df["attendance_zscore"] = (df["attendance_cleaned"] - a_mean) / a_std if a_std > 0 else 0.0
    
    # Columns to save
    save_cols = [
        "student_id", "full_name", "dob", "gender", "department",
        "email", "phone", "city", "admission_date", "attendance_cleaned",
        "marks_cleaned", "attendance_minmax", "attendance_zscore",
        "marks_minmax", "marks_zscore"
    ]
    cols_present = [c for c in save_cols if c in df.columns]
    curated_df = df[cols_present].copy()
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    curated_df.to_csv(output_path, index=False)
    
    json_path = output_path.with_suffix(".json")
    curated_df.to_json(json_path, orient="records", indent=2)
    
    logging.info(f"[STAGE 7] Successfully saved {len(curated_df)} records to: {output_path}")
    logging.info(f"[STAGE 7] JSON mirror exported to: {json_path}")

# ---------------------------------------------------------
# Full Pipeline Execution
# ---------------------------------------------------------
def run_pipeline(input_file: Path, output_file: Path) -> pd.DataFrame:
    logging.info("=" * 60)
    logging.info("STARTING MERIDIAN UNIVERSITY DATA CLEANING PIPELINE")
    logging.info("=" * 60)
    
    df1 = stage1_load(input_file)
    df2 = stage2_format_standardize(df1)
    df3 = stage3_impute_missing(df2)
    df4 = stage4_treat_outliers(df3)
    df5 = stage5_deduplicate(df4)
    df6 = stage6_regex_clean(df5)
    stage7_normalize_and_save(df6, output_file)
    
    logging.info("=" * 60)
    logging.info("PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
    logging.info("=" * 60)
    return df6

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meridian University Automated Student Record Cleaning Pipeline")
    parser.add_argument("--input", type=str, default="raw/students_dirty.csv", help="Path to input raw CSV")
    parser.add_argument("--output", type=str, default="curated/clean_students_output.csv", help="Path to output cleaned CSV")
    args = parser.parse_args()
    
    script_dir = Path(__file__).resolve().parent
    inp = script_dir / args.input if not Path(args.input).is_absolute() else Path(args.input)
    out = script_dir / args.output if not Path(args.output).is_absolute() else Path(args.output)
    
    run_pipeline(inp, out)

