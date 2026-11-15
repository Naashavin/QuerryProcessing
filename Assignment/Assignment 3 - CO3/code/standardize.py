"""
Task 3: Formatting Data and Standardizing Values
Author: Avinaash A (Reg. No: 192324260)
Course: DSA0501 - Query Processing for Data Science
"""

import sys
import re
from pathlib import Path
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
RAW_CSV = BASE_DIR / "raw" / "students_dirty.csv"
STAGED_DIR = BASE_DIR / "staged"
STAGED_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# Canonical Department Mapping Dictionary
# ---------------------------------------------------------
DEPT_CANONICAL_MAP = {
    # Computer Science and Engineering
    "computer science and engineering": "Computer Science and Engineering",
    "computer science & engineering": "Computer Science and Engineering",
    "computer science": "Computer Science and Engineering",
    "comp sci & engg": "Computer Science and Engineering",
    "comp. sci.": "Computer Science and Engineering",
    "comp sci": "Computer Science and Engineering",
    "cse": "Computer Science and Engineering",
    "cs": "Computer Science and Engineering",
    
    # Information Technology
    "information technology": "Information Technology",
    "information tech": "Information Technology",
    "info tech": "Information Technology",
    "infotech": "Information Technology",
    "it dept": "Information Technology",
    "i.t.": "Information Technology",
    "it": "Information Technology",
    
    # Electronics and Communication Engineering
    "electronics and communication engineering": "Electronics and Communication Engineering",
    "electronics & communication engineering": "Electronics and Communication Engineering",
    "electronics & comm.": "Electronics and Communication Engineering",
    "electronics & comm engg": "Electronics and Communication Engineering",
    "electronics and comm": "Electronics and Communication Engineering",
    "electronics": "Electronics and Communication Engineering",
    "e.c.e.": "Electronics and Communication Engineering",
    "ece": "Electronics and Communication Engineering",
    
    # Mechanical Engineering
    "mechanical engineering": "Mechanical Engineering",
    "mechanical eng.": "Mechanical Engineering",
    "mech. engineering": "Mechanical Engineering",
    "mech engg": "Mechanical Engineering",
    "mechanical": "Mechanical Engineering",
    "mech": "Mechanical Engineering",
    
    # Civil Engineering
    "civil engineering": "Civil Engineering",
    "civil dept": "Civil Engineering",
    "civ. engg.": "Civil Engineering",
    "civil engg": "Civil Engineering",
    "civil": "Civil Engineering",
    "c.e.": "Civil Engineering",
    
    # Business Administration
    "business administration": "Business Administration",
    "business management": "Business Administration",
    "business admin": "Business Administration",
    "mgmt studies": "Business Administration",
    "management": "Business Administration",
    "mba": "Business Administration",
    "bba": "Business Administration"
}

# ---------------------------------------------------------
# Smart Name Title-Casing (Handling O'Brien, de Souza, initials)
# ---------------------------------------------------------
def clean_name_string(raw_name: str) -> str:
    if pd.isna(raw_name):
        return raw_name
    s = str(raw_name).strip()
    # Normalize comma separated 'Last, First'
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            s = f"{parts[1]} {parts[0]}"
    
    # Collapse multiple whitespaces
    s = re.sub(r"\s+", " ", s)
    
    # Word by word capitalization with particle handling
    words = s.split(" ")
    formatted = []
    particles = {"de", "da", "di", "van", "von", "del", "della"}
    
    for i, w in enumerate(words):
        w_lower = w.lower()
        if i > 0 and w_lower in particles:
            formatted.append(w_lower)
        elif "'" in w: # Handle O'Brien, D'Silva
            sub_parts = w.split("'")
            formatted.append("'".join(p.capitalize() for p in sub_parts))
        elif re.match(r"^[a-zA-Z]\.$", w): # Initial like R. or S.
            formatted.append(w.upper())
        elif len(w) == 1: # Single letter initial without dot
            formatted.append(f"{w.upper()}.")
        else:
            formatted.append(w.capitalize())
            
    return " ".join(formatted)

# ---------------------------------------------------------
# Date Parser with ISO 8601 Output & Ambiguity Resolution
# ---------------------------------------------------------
def parse_date_to_iso(date_str: str) -> tuple:
    """
    Returns (iso_str or np.nan, flag)
    Ambiguity Rule: In Indian university administration, standard format is DD-MM-YYYY.
    Therefore, for '03-12-2003', it is resolved as 3rd Dec 2003.
    """
    if pd.isna(date_str):
        return np.nan, "MISSING_DATE"
    s = str(date_str).strip()
    if s in ["NA", "-", "?", "null", "N/A", "", "none"]:
        return np.nan, "MISSING_DATE"
        
    # Check for known formats using pd.to_datetime with dayfirst=True
    try:
        dt = pd.to_datetime(s, dayfirst=True, format="mixed")
        # Sanity check year range (1995 - 2026)
        if dt.year < 1995 or dt.year > 2026:
            return np.nan, "UNREASONABLE_YEAR"
        return dt.strftime("%Y-%m-%d"), "VALID"
    except Exception:
        return np.nan, "UNPARSEABLE_DATE"

# ---------------------------------------------------------
# Phone Number Normalization
# ---------------------------------------------------------
def normalize_indian_phone(phone_str: str) -> tuple:
    """
    Extracts 10 digits starting with 6, 7, 8, 9.
    Returns (clean_10_digit or np.nan, status_flag)
    """
    if pd.isna(phone_str):
        return np.nan, "MISSING_PHONE"
    s = str(phone_str).strip()
    if s in ["NA", "-", "?", "null", "N/A", "", "none"]:
        return np.nan, "MISSING_PHONE"
        
    # Extract only digits
    digits = re.sub(r"\D", "", s)
    
    # Strip country code 91 if 12 digits
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    # Strip leading 0 if 11 digits
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
        
    if len(digits) == 10 and digits[0] in "6789":
        return digits, "VALID"
    else:
        return np.nan, f"INVALID_PHONE_{len(digits)}_DIGITS"

# ---------------------------------------------------------
# Gender Normalizer
# ---------------------------------------------------------
def standardize_gender(g_str: str) -> str:
    if pd.isna(g_str):
        return np.nan
    s = str(g_str).strip().lower()
    if s in ["f", "female", "fem"]:
        return "Female"
    elif s in ["m", "male"]:
        return "Male"
    else:
        return np.nan

# ---------------------------------------------------------
# Department Normalizer
# ---------------------------------------------------------
def standardize_department(dept_str: str) -> str:
    if pd.isna(dept_str):
        return np.nan
    s = str(dept_str).strip().lower()
    s = re.sub(r"\s+", " ", s)
    
    # Check exact match
    if s in DEPT_CANONICAL_MAP:
        return DEPT_CANONICAL_MAP[s]
        
    # Check without dots
    s_nodots = s.replace(".", "").strip()
    if s_nodots in DEPT_CANONICAL_MAP:
        return DEPT_CANONICAL_MAP[s_nodots]
        
    # Check rstrip dots
    s_rstrip = s.rstrip(".")
    if s_rstrip in DEPT_CANONICAL_MAP:
        return DEPT_CANONICAL_MAP[s_rstrip]

    # Keyword based matching for remaining variants
    if "comp" in s or "cs" in s:
        return "Computer Science and Engineering"
    elif "info" in s or s in ["it", "i.t.", "i.t"]:
        return "Information Technology"
    elif "elect" in s or "ece" in s:
        return "Electronics and Communication Engineering"
    elif "mech" in s:
        return "Mechanical Engineering"
    elif "civ" in s or s in ["ce", "c.e.", "c.e"]:
        return "Civil Engineering"
    elif "bus" in s or "mgmt" in s or "admin" in s or "mba" in s or "bba" in s:
        return "Business Administration"
        
    # Fallback to title-case if unmapped
    return str(dept_str).strip().title()

def run_standardization():
    print("=" * 80)
    print("TASK 3: FORMATTING DATA AND STANDARDIZING VALUES")
    print("=" * 80)
    
    na_tokens = ["NA", "-", "?", "null", "N/A", "none", "nan", ""]
    df = pd.read_csv(RAW_CSV, na_values=na_tokens, keep_default_na=True, dtype=str)
    raw_df = df.copy()
    
    print("\n1. Applying Standardization Rules...")
    # Student ID: uppercase, strip whitespace
    df["student_id"] = df["student_id"].str.strip().str.upper()
    
    # Full Name: smart title casing
    df["full_name"] = df["full_name"].apply(clean_name_string)
    
    # Gender
    df["gender"] = df["gender"].apply(standardize_gender)
    
    # Department
    df["department"] = df["department"].apply(standardize_department)
    
    # Email: lowercase, strip
    df["email"] = df["email"].str.strip().str.lower()
    
    # City: title-cased, strip
    df["city"] = df["city"].str.strip().str.title()
    
    # Date of Birth (DOB)
    dob_results = df["dob"].apply(parse_date_to_iso)
    df["dob"] = [r[0] for r in dob_results]
    df["dob_flag"] = [r[1] for r in dob_results]
    
    # Admission Date
    adm_results = df["admission_date"].apply(parse_date_to_iso)
    df["admission_date"] = [r[0] for r in adm_results]
    df["adm_flag"] = [r[1] for r in adm_results]
    
    # Phone Normalization
    phone_results = df["phone"].apply(normalize_indian_phone)
    df["phone"] = [r[0] for r in phone_results]
    df["phone_flag"] = [r[1] for r in phone_results]
    
    # Marks and Attendance to numeric
    df["attendance_pct"] = pd.to_numeric(df["attendance_pct"], errors="coerce")
    df["marks"] = pd.to_numeric(df["marks"], errors="coerce")
    
    print("\n2. Before vs After Distinct Value Count (6 Key Columns):")
    cols_to_compare = ["student_id", "gender", "department", "dob", "phone", "city"]
    comparison = []
    for c in cols_to_compare:
        before_cnt = raw_df[c].nunique(dropna=True)
        after_cnt = df[c].nunique(dropna=True)
        comparison.append({
            "Column": c,
            "Raw Distinct Count": before_cnt,
            "Cleaned Distinct Count": after_cnt,
            "Reduction / Consolidation": f"{before_cnt - after_cnt} variants collapsed"
        })
    print(pd.DataFrame(comparison).to_string(index=False))
    
    print("\n3. Unparseable Dates & Phone Flags Count:")
    print("DOB Flags:", df["dob_flag"].value_counts().to_dict())
    print("Phone Flags:", df["phone_flag"].value_counts().to_dict())
    
    print("\n4. Sample Standardized Rows (5 Samples):")
    print(df[["student_id", "full_name", "dob", "gender", "department", "phone", "city"]].head(5).to_string(index=False))
    
    out_staged = STAGED_DIR / "students_stage3_standardized.csv"
    df.to_csv(out_staged, index=False)
    print(f"\nSaved Standardized Data to: {out_staged}")
    return df

if __name__ == "__main__":
    run_standardization()
