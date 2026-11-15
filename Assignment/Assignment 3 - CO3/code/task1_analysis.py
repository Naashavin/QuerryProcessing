"""
Task 1: Understanding Data Quality and Why Clean Data Matters
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

def run_task1():
    print("=" * 80)
    print("TASK 1: DATA QUALITY IMPACT ANALYSIS & RAW DATA BASELINE")
    print("=" * 80)
    
    # Load raw data without interpretation
    df_raw = pd.read_csv(RAW_CSV, dtype=str)
    print(f"\n1. Raw Dataset Dimensions: {df_raw.shape[0]} rows, {df_raw.shape[1]} columns")
    print("\n2. First 5 Rows (head):")
    print(df_raw.head(5).to_string())
    
    # Raw Analysis 1: Average Marks per Department (raw string aggregation)
    print("\n" + "-" * 60)
    print("ANALYSIS 1 (RAW): Average Marks per Department (Raw Data)")
    print("-" * 60)
    # Convert marks to numeric where possible, ignoring errors
    df_raw["marks_num"] = pd.to_numeric(df_raw["marks"], errors="coerce")
    raw_dept_marks = df_raw.groupby("department")["marks_num"].agg(["count", "mean", "min", "max"]).reset_index()
    print(raw_dept_marks.head(15).to_string(index=False))
    
    # Raw Analysis 2: Students with Attendance < 75%
    print("\n" + "-" * 60)
    print("ANALYSIS 2 (RAW): Count of Students with Attendance < 75%")
    print("-" * 60)
    df_raw["att_num"] = pd.to_numeric(df_raw["attendance_pct"], errors="coerce")
    shortage_count = (df_raw["att_num"] < 75.0).sum()
    missing_att = df_raw["att_num"].isna().sum()
    outlier_att = (df_raw["att_num"] > 100.0).sum()
    print(f"Total records evaluated: {len(df_raw)}")
    print(f"Students with raw attendance < 75%: {shortage_count} ({shortage_count/len(df_raw)*100:.2f}%)")
    print(f"Students with missing/unparseable attendance: {missing_att} ({missing_att/len(df_raw)*100:.2f}%)")
    print(f"Students with impossible attendance (> 100%): {outlier_att} ({outlier_att/len(df_raw)*100:.2f}%)")
    
    print("\nTask 1 Baseline Analysis Completed Successfully.")

if __name__ == "__main__":
    run_task1()

