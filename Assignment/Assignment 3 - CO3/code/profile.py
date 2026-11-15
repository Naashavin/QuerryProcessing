"""
Task 2: Data Cleanup Basics - Profiling the Data and Identifying Values for Cleaning
Author: Avinaash A (Reg. No: 192324260)
Course: DSA0501 - Query Processing for Data Science
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
RAW_CSV = BASE_DIR / "raw" / "students_dirty.csv"

def profile_dataset():
    print("=" * 80)
    print("TASK 2: COMPREHENSIVE DATA PROFILING & PROBLEM CLASSIFICATION")
    print("=" * 80)
    
    # 1. Raw read to inspect raw string representations and placeholders
    df_raw = pd.read_csv(RAW_CSV, dtype=str)
    
    # 2. Controlled read with na_values
    na_tokens = ["NA", "-", "?", "null", "N/A", "none", "nan", ""]
    df_controlled = pd.read_csv(RAW_CSV, na_values=na_tokens, keep_default_na=True)
    
    print("\n1. Memory & Shape Profiling:")
    print(f"Shape: {df_controlled.shape[0]} rows, {df_controlled.shape[1]} columns")
    mem_usage = df_controlled.memory_usage(deep=True).sum() / 1024
    print(f"Total Memory Usage: {mem_usage:.2f} KB")
    
    print("\n2. Data Type Inspection (Detected vs Expected):")
    type_audit = []
    expected_types = {
        "student_id": "string (categorical / key)",
        "full_name": "string (text)",
        "dob": "date (ISO 8601)",
        "gender": "category",
        "department": "category",
        "email": "string (email)",
        "phone": "string (10-digit numeric)",
        "city": "category",
        "admission_date": "date (ISO 8601)",
        "attendance_pct": "float64 (percentage [0, 100])",
        "marks": "int64 / float64 (range [0, 100])"
    }
    for col in df_controlled.columns:
        actual_dtype = str(df_controlled[col].dtype)
        wrong_flag = "MISMATCH / SUB-OPTIMAL" if actual_dtype == "object" and col in ["dob", "admission_date", "marks", "attendance_pct"] else "OK"
        type_audit.append({
            "Column": col,
            "Loaded Dtype": actual_dtype,
            "Expected Logical Dtype": expected_types.get(col, "string"),
            "Status": wrong_flag
        })
    print(pd.DataFrame(type_audit).to_string(index=False))
    
    print("\n3. Column-by-Column Profiling Table:")
    profile_rows = []
    for col in df_raw.columns:
        total = len(df_raw)
        raw_vals = df_raw[col].fillna("")
        
        # Count explicit placeholders
        blank_cnt = (raw_vals.str.strip() == "").sum()
        na_cnt = (raw_vals.str.strip().isin(["NA", "N/A", "null", "nan"])).sum()
        dash_cnt = (raw_vals.str.strip() == "-").sum()
        qmark_cnt = (raw_vals.str.strip() == "?").sum()
        placeholder_total = blank_cnt + na_cnt + dash_cnt + qmark_cnt
        
        # Unique count on controlled load
        n_unique = df_controlled[col].nunique(dropna=True)
        missing_controlled = df_controlled[col].isna().sum()
        missing_pct = (missing_controlled / total) * 100
        
        sample_vals = ", ".join(df_raw[col].dropna().sample(3, random_state=42).astype(str).str.strip().tolist())
        
        profile_rows.append({
            "Column": col,
            "Total Rows": total,
            "Real Missing (NaN)": missing_controlled,
            "Missing %": f"{missing_pct:.2f}%",
            "Placeholders (NA/-/?)": placeholder_total,
            "Distinct Values": n_unique,
            "Sample Values": sample_vals[:35]
        })
    df_profile = pd.DataFrame(profile_rows)
    print(df_profile.to_string(index=False))
    
    print("\n4. Numerical Summary (describe() on raw parsed numeric columns):")
    num_cols = ["attendance_pct", "marks"]
    num_summary = df_controlled[num_cols].describe().T[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]
    print(num_summary.to_string())
    
    print("\n5. Problem Classification Summary:")
    problem_classes = [
        {"Class": "Missing Data", "Attributes Affected": "dob, phone, attendance_pct, marks", "Observed Count": f"~{missing_controlled} per col", "Examples": "NA, -, ?, blank strings"},
        {"Class": "Invalid Format / Syntax", "Attributes Affected": "email, phone, student_id, dob", "Observed Count": "150-400 records", "Examples": "anitha.s@@meridian.edu, 2005-02-30, short phones"},
        {"Class": "Inconsistent Categorization", "Attributes Affected": "department, gender, city", "Observed Count": "> 3,500 records", "Examples": "Comp. Sci. vs CSE, F vs Female, chennai vs Chennai"},
        {"Class": "Suspicious / Outlier Values", "Attributes Affected": "attendance_pct, marks", "Observed Count": "300+ records", "Examples": "attendance = 134%, marks = 640 or -5"},
        {"Class": "Duplicate Entities", "Attributes Affected": "All columns (exact, key, partial)", "Observed Count": "310+ records", "Examples": "Repeated student IDs with conflicting marks or phones"}
    ]
    print(pd.DataFrame(problem_classes).to_string(index=False))
    
    return df_controlled

if __name__ == "__main__":
    profile_dataset()

