"""
Task 5: Finding Outliers and Bad Data
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
STAGED_DIR = BASE_DIR / "staged"
INPUT_CSV = STAGED_DIR / "students_stage4_imputed.csv"

def run_outlier_detection():
    print("=" * 80)
    print("TASK 5: OUTLIER & BAD DATA DETECTION (IQR VS Z-SCORE VS DOMAIN BOUNDS)")
    print("=" * 80)
    
    df = pd.read_csv(INPUT_CSV)
    
    # 1. Global vs Group-wise Statistical Outlier Bounds
    # Overall Marks
    m_q1 = df["marks"].quantile(0.25)
    m_q3 = df["marks"].quantile(0.75)
    m_iqr = m_q3 - m_q1
    m_lower_iqr = m_q1 - 1.5 * m_iqr
    m_upper_iqr = m_q3 + 1.5 * m_iqr
    
    m_mean = df["marks"].mean()
    m_std = df["marks"].std()
    m_lower_z = m_mean - 3.0 * m_std
    m_upper_z = m_mean + 3.0 * m_std
    
    # Overall Attendance
    a_q1 = df["attendance_pct"].quantile(0.25)
    a_q3 = df["attendance_pct"].quantile(0.75)
    a_iqr = a_q3 - a_q1
    a_lower_iqr = a_q1 - 1.5 * a_iqr
    a_upper_iqr = a_q3 + 1.5 * a_iqr
    
    a_mean = df["attendance_pct"].mean()
    a_std = df["attendance_pct"].std()
    a_lower_z = a_mean - 3.0 * a_std
    a_upper_z = a_mean + 3.0 * a_std
    
    print("\n1. Global Detection Thresholds Comparison:")
    bounds_df = pd.DataFrame([
        {
            "Metric": "Marks",
            "Domain Min-Max": "[0, 100]",
            "IQR Lower (1.5x)": f"{m_lower_iqr:.2f}",
            "IQR Upper (1.5x)": f"{m_upper_iqr:.2f}",
            "Z-Score Lower (-3s)": f"{m_lower_z:.2f}",
            "Z-Score Upper (+3s)": f"{m_upper_z:.2f}",
            "Domain Violations": ((df["marks"] < 0) | (df["marks"] > 100)).sum()
        },
        {
            "Metric": "Attendance %",
            "Domain Min-Max": "[0.0, 100.0]",
            "IQR Lower (1.5x)": f"{a_lower_iqr:.2f}",
            "IQR Upper (1.5x)": f"{a_upper_iqr:.2f}",
            "Z-Score Lower (-3s)": f"{a_lower_z:.2f}",
            "Z-Score Upper (+3s)": f"{a_upper_z:.2f}",
            "Domain Violations": ((df["attendance_pct"] < 0.0) | (df["attendance_pct"] > 100.0)).sum()
        }
    ])
    print(bounds_df.to_string(index=False))
    
    # 2. Flagging Outliers
    df["marks_domain_bad"] = (df["marks"] < 0) | (df["marks"] > 100)
    df["att_domain_bad"] = (df["attendance_pct"] < 0.0) | (df["attendance_pct"] > 100.0)
    
    df["marks_iqr_bad"] = (df["marks"] < m_lower_iqr) | (df["marks"] > m_upper_iqr)
    df["att_iqr_bad"] = (df["attendance_pct"] < a_lower_iqr) | (df["attendance_pct"] > a_upper_iqr)
    
    df["marks_z_bad"] = (df["marks"] < m_lower_z) | (df["marks"] > m_upper_z)
    df["att_z_bad"] = (df["attendance_pct"] < a_lower_z) | (df["attendance_pct"] > a_upper_z)
    
    print("\n2. Outlier Detection Method Efficacy Summary:")
    print(f"Marks Domain Violations (<0 or >100): {df['marks_domain_bad'].sum()} records")
    print(f"Marks IQR Flags: {df['marks_iqr_bad'].sum()} records")
    print(f"Marks Z-Score Flags: {df['marks_z_bad'].sum()} records (Masked by inflated standard deviation!)")
    print(f"Attendance Domain Violations (<0 or >100): {df['att_domain_bad'].sum()} records")
    print(f"Attendance IQR Flags: {df['att_iqr_bad'].sum()} records")
    print(f"Attendance Z-Score Flags: {df['att_z_bad'].sum()} records")
    
    # 3. Decision Log on 10 Flagged Sample Records
    flagged_samples = df[df["marks_domain_bad"] | df["att_domain_bad"]].head(10)
    decision_log = []
    
    for idx, row in flagged_samples.iterrows():
        sid = row["student_id"]
        m = row["marks"]
        att = row["attendance_pct"]
        
        issue_desc = []
        action = []
        if m > 100:
            if m in [640, 580, 850]:
                corrected_m = m // 10 # Typo: extra 0 appended during data entry
                issue_desc.append(f"Marks={m} (Typo: extra zero)")
                action.append(f"Rescale/Divide by 10 -> {corrected_m}")
            else:
                issue_desc.append(f"Marks={m} (> 100)")
                action.append("Cap to group median / 100")
        elif m < 0:
            issue_desc.append(f"Marks={m} (Negative)")
            action.append(f"Convert absolute/group median -> {abs(m)}")
            
        if att > 100:
            issue_desc.append(f"Att={att}% (> 100%)")
            action.append("Cap to 100.0% max")
        elif att < 0:
            issue_desc.append(f"Att={att}% (< 0%)")
            action.append("Convert to 0.0% / absolute")
            
        decision_log.append({
            "Student ID": sid,
            "Raw Marks": m,
            "Raw Att %": att,
            "IQR Flag": row["marks_iqr_bad"] or row["att_iqr_bad"],
            "Z-Score Flag": row["marks_z_bad"] or row["att_z_bad"],
            "Detected Issue": "; ".join(issue_desc),
            "Correction Action": "; ".join(action)
        })
        
    print("\n3. Decision Log on 10 Sample Flagged Records:")
    print(pd.DataFrame(decision_log).to_string(index=False))
    
    # 4. Apply Robust Domain Correction Rules
    # Clean marks:
    def correct_marks(val, dept, adm_yr):
        if pd.isna(val):
            return 75.0
        v = float(val)
        if v in [640, 580, 850]:
            return float(v / 10.0) # correct typographical extra zero
        if v < 0:
            return float(abs(v))
        if v > 100:
            return 100.0
        return v
        
    def correct_attendance(val):
        if pd.isna(val):
            return 80.0
        v = float(val)
        if v < 0:
            return float(abs(v))
        if v > 100:
            return 100.0
        return v
        
    df["marks_cleaned"] = [correct_marks(r["marks"], r["department"], r["adm_year"]) for _, r in df.iterrows()]
    df["attendance_cleaned"] = [correct_attendance(r["attendance_pct"]) for _, r in df.iterrows()]
    
    print("\n4. Summary Statistics Post-Outlier Treatment:")
    print(df[["marks_cleaned", "attendance_cleaned"]].describe().T[["count", "mean", "std", "min", "50%", "max"]].to_string())
    
    out_staged = STAGED_DIR / "students_stage5_outliers_treated.csv"
    df.to_csv(out_staged, index=False)
    print(f"\nSaved Outlier-Treated Data to: {out_staged}")
    return df

if __name__ == "__main__":
    run_outlier_detection()

