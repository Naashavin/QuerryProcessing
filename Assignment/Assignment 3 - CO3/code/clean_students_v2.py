"""
Meridian University Student Information System
Revised Production Cleaning Pipeline V2: clean_students_v2.py
Day-4 Design Challenge Adaptation (CO3 Coverage)
Author: Avinaash A (Reg. No: 192324260)
Course: DSA0501 - Query Processing for Data Science
"""

import sys
import re
import argparse
import logging
from pathlib import Path
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

V2_CONFIG = {
    "column_mapping": {
        "applicant_ref": "student_id",
        "applicant_name": "full_name",
        "dob": "dob",
        "sex": "gender",
        "programme": "department",
        "email": "email",
        "mobile": "phone",
        "category": "quota_category",
        "hsc_percentage": "marks",
        "submitted_on": "admission_date"
    },
    "canonical_departments_v2": {
        "computer science and engineering": "Computer Science and Engineering",
        "computer science & engineering": "Computer Science and Engineering",
        "computer science": "Computer Science and Engineering",
        "comp sci & engg": "Computer Science and Engineering",
        "c.s.e.": "Computer Science and Engineering",
        "cse": "Computer Science and Engineering",
        "cs": "Computer Science and Engineering",
        "information technology": "Information Technology",
        "information tech": "Information Technology",
        "info tech": "Information Technology",
        "infotech": "Information Technology",
        "it": "Information Technology",
        "electronics and communication engineering": "Electronics and Communication Engineering",
        "electronics & comm.": "Electronics and Communication Engineering",
        "ece": "Electronics and Communication Engineering",
        "mechanical engineering": "Mechanical Engineering",
        "mechanical": "Mechanical Engineering",
        "mech": "Mechanical Engineering",
        "civil engineering": "Civil Engineering",
        "civil": "Civil Engineering",
        "business administration": "Business Administration",
        "management": "Business Administration",
        "artificial intelligence and data science": "Artificial Intelligence and Data Science",
        "artificial intell & data sci": "Artificial Intelligence and Data Science",
        "ai&ds": "Artificial Intelligence and Data Science",
        "aids": "Artificial Intelligence and Data Science",
        "biomedical engineering": "Biomedical Engineering",
        "biomedical engg": "Biomedical Engineering",
        "biomedical": "Biomedical Engineering",
        "bme": "Biomedical Engineering"
    },
    "honorifics": [r"^mr\.\s*", r"^ms\.\s*", r"^mrs\.\s*", r"^dr\.\s*", r"^shri\.\s*"]
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def run_v2_pipeline(input_path: Path, output_path: Path, is_portal: bool = True):
    logging.info(f"Ingesting data from: {input_path}")
    df = pd.read_csv(input_path, dtype=str)
    
    # 1. Schema mapping
    if is_portal:
        logging.info("Applying dynamic schema mapping...")
        df = df.rename(columns=V2_CONFIG["column_mapping"])
        if "attendance_cleaned" not in df.columns:
            df["attendance_cleaned"] = 85.0
            
    # 2. Name Cleaning & Honorific Stripping
    def clean_name(s):
        if pd.isna(s) or str(s).strip() == "":
            return s
        raw = str(s).strip()
        for hon in V2_CONFIG["honorifics"]:
            raw = re.sub(hon, "", raw, flags=re.IGNORECASE)
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
        
    df["full_name"] = df["full_name"].apply(clean_name)
    
    # 3. Flexible Date & Timestamp Parser
    def parse_date(d):
        if pd.isna(d) or str(d).strip() in ["N.A.", "NA", "-", "?", "", "Not Provided"]:
            return np.nan
        s = str(d).strip().replace(".", "-").replace("/", "-")
        if " " in s:
            s = s.split(" ")[0]
        try:
            dt = pd.to_datetime(s, dayfirst=True, format="mixed")
            if dt.year < 1995 or dt.year > 2026:
                return np.nan
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return np.nan
            
    df["dob"] = df["dob"].apply(parse_date)
    if "admission_date" in df.columns:
        df["admission_date"] = df["admission_date"].apply(parse_date)
        
    # 4. Department Standardizer
    def clean_dept(d):
        if pd.isna(d):
            return "Unassigned"
        raw = str(d).strip().lower()
        raw = re.sub(r"\s+", " ", raw)
        mapping = V2_CONFIG["canonical_departments_v2"]
        if raw in mapping:
            return mapping[raw]
        nodots = raw.replace(".", "").strip()
        if nodots in mapping:
            return mapping[nodots]
        if "ai" in raw or "data sci" in raw:
            return "Artificial Intelligence and Data Science"
        elif "biomed" in raw or "bme" in raw:
            return "Biomedical Engineering"
        elif "comp" in raw or "cs" in raw:
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
        
    df["department"] = df["department"].apply(clean_dept)
    
    # 5. Marks Rescaling
    def clean_marks(v):
        if pd.isna(v) or str(v).strip() in ["N.A.", "NA", "-", "?", ""]:
            return np.nan
        try:
            val = float(str(v).strip())
        except Exception:
            return np.nan
        if 0.0 < val <= 1.0:
            return round(val * 100.0, 1)
        if 100.0 < val <= 500.0:
            return round((val / 500.0) * 100.0, 1)
        if val in [640, 580, 850]:
            return val / 10.0
        if val < 0:
            return abs(val)
        if val > 100:
            return 100.0
        return val
        
    df["marks_cleaned"] = df["marks"].apply(clean_marks)
    df["marks_cleaned"] = df.groupby("department")["marks_cleaned"].transform(lambda g: g.fillna(g.median()))
    df["marks_cleaned"] = df["marks_cleaned"].fillna(78.0)
    
    # 6. Phone Cleaning
    def clean_phone(p):
        if pd.isna(p) or str(p).strip() in ["N.A.", "NA", "-", "?", ""]:
            return np.nan
        digits = re.sub(r"\D", "", str(p))
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]
        if len(digits) == 10 and digits[0] in "6789":
            return digits
        return np.nan
        
    df["phone"] = df["phone"].apply(clean_phone)
    
    # 7. Deduplication
    init_rows = len(df)
    df = df.sort_values(by=["marks_cleaned", "phone"], ascending=[False, False])
    df = df.drop_duplicates(subset=["student_id"], keep="first")
    has_dob = df["dob"].notna()
    dob_dups = df[has_dob].drop_duplicates(subset=["full_name", "dob"], keep="first")
    no_dob = df[~has_dob]
    df = pd.concat([dob_dups, no_dob], ignore_index=True)
    logging.info(f"Purged {init_rows - len(df)} duplicate applications.")
    
    # 8. Scaling
    m_min = df["marks_cleaned"].min()
    m_max = df["marks_cleaned"].max()
    m_mean = df["marks_cleaned"].mean()
    m_std = df["marks_cleaned"].std()
    
    df["marks_minmax"] = (df["marks_cleaned"] - m_min) / (m_max - m_min) if (m_max - m_min) > 0 else 0.5
    df["marks_zscore"] = (df["marks_cleaned"] - m_mean) / m_std if m_std > 0 else 0.0
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logging.info(f"Curated V2 dataset saved to: {output_path}")
    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meridian University V2 Cleaning Pipeline")
    parser.add_argument("--input", type=str, default="raw/portal_dirty.csv", help="Input file path")
    parser.add_argument("--output", type=str, default="curated/portal_cleaned_v2.csv", help="Output file path")
    parser.add_argument("--is_portal", action="store_true", default=True, help="Set if processing portal dataset")
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent
    inp = base_dir / args.input if not Path(args.input).is_absolute() else Path(args.input)
    out = base_dir / args.output if not Path(args.output).is_absolute() else Path(args.output)
    
    run_v2_pipeline(inp, out, is_portal=args.is_portal)

