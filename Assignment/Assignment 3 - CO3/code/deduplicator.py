"""
Task 6: Finding Duplicates, Designing Survivorship Rules & Merging Records
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
INPUT_CSV = STAGED_DIR / "students_stage5_outliers_treated.csv"

def run_deduplication():
    print("=" * 80)
    print("TASK 6: MULTI-LEVEL DUPLICATE DETECTION & SURVIVORSHIP MERGE")
    print("=" * 80)
    
    df = pd.read_csv(INPUT_CSV)
    initial_count = len(df)
    print(f"Initial Record Count: {initial_count}")
    
    # 1. Exact Duplicate Detection
    core_cols = ["student_id", "full_name", "dob", "gender", "department", "email", "phone", "city", "admission_date"]
    exact_mask = df.duplicated(subset=core_cols, keep="first")
    exact_dup_count = exact_mask.sum()
    print(f"\n1. Exact Duplicates Found: {exact_dup_count} records")
    
    # Deduplicate exact
    df_dedup_exact = df[~exact_mask].copy()
    removed_records = []
    for idx, row in df[exact_mask].iterrows():
        removed_records.append({
            "student_id": row["student_id"],
            "full_name": row["full_name"],
            "dob": row["dob"],
            "dup_type": "EXACT_DUPLICATE",
            "reason": "Identical demographic and academic attributes across all columns"
        })
        
    # 2. Key Duplicates (Same student_id, conflicting attributes)
    key_dup_mask = df_dedup_exact.duplicated(subset=["student_id"], keep=False)
    key_dup_groups = df_dedup_exact[key_dup_mask].groupby("student_id")
    print(f"2. Key Duplicates (Conflicting Records under same student_id): {len(key_dup_groups)} student IDs affected")
    
    # Apply Survivorship Rule for Key Duplicates:
    # Priority: Non-null Phone > Non-null DOB > Latest Admission Date
    surviving_key_rows = []
    for sid, group in key_dup_groups:
        sorted_g = group.sort_values(
            by=["phone_flag", "dob_flag", "admission_date", "marks_cleaned"],
            ascending=[False, False, False, False]
        )
        survivor = sorted_g.iloc[0]
        surviving_key_rows.append(survivor["student_id"])
        
        # Log dropped conflicting variants
        for _, dropped in sorted_g.iloc[1:].iterrows():
            removed_records.append({
                "student_id": dropped["student_id"],
                "full_name": dropped["full_name"],
                "dob": dropped["dob"],
                "dup_type": "KEY_CONFLICT",
                "reason": f"Conflicting phone/marks superseded by survivor with phone={survivor['phone']}"
            })
            
    # Filter out non-surviving key duplicate rows
    drop_key_indices = []
    for sid, group in key_dup_groups:
        survivor_idx = group.sort_values(
            by=["phone_flag", "dob_flag", "admission_date", "marks_cleaned"],
            ascending=[False, False, False, False]
        ).index[0]
        for dropped_idx in group.index:
            if dropped_idx != survivor_idx:
                drop_key_indices.append(dropped_idx)
                
    df_after_key = df_dedup_exact.drop(index=drop_key_indices)
    
    # 3. Partial Duplicates (Same full_name and dob, but different student_id)
    # Ignore missing dob to avoid false clusters on NaN DOB
    has_valid_dob = df_after_key["dob"].notna() & (df_after_key["dob"] != "")
    partial_dup_mask = df_after_key[has_valid_dob].duplicated(subset=["full_name", "dob"], keep=False)
    partial_groups = df_after_key[has_valid_dob][partial_dup_mask].groupby(["full_name", "dob"])
    print(f"3. Partial Duplicates (Same Name & DOB under differing IDs): {len(partial_groups)} clusters found")
    
    drop_partial_indices = []
    for (name, dob), group in partial_groups:
        # Survivor: Oldest admission date (original enrollment) or most complete contact
        sorted_p = group.sort_values(by=["admission_date", "student_id"], ascending=[True, True])
        survivor = sorted_p.iloc[0]
        
        for _, dropped in sorted_p.iloc[1:].iterrows():
            drop_partial_indices.append(dropped.name)
            removed_records.append({
                "student_id": dropped["student_id"],
                "full_name": dropped["full_name"],
                "dob": dropped["dob"],
                "dup_type": "PARTIAL_NAME_DOB",
                "reason": f"Duplicate student enrollment under secondary ID; primary retained is {survivor['student_id']}"
            })
            
    df_clean_dedup = df_after_key.drop(index=drop_partial_indices).copy()
    final_count = len(df_clean_dedup)
    total_removed = initial_count - final_count
    
    print("\n4. Deduplication Summary:")
    print(f"Records before deduplication: {initial_count}")
    print(f"Exact duplicates removed:    {exact_dup_count}")
    print(f"Key conflicts removed:       {len(drop_key_indices)}")
    print(f"Partial duplicates removed:  {len(drop_partial_indices)}")
    print(f"Total duplicate rows purged: {total_removed} ({(total_removed/initial_count)*100:.2f}%)")
    print(f"Clean surviving records:     {final_count}")
    
    # Export Audit Log
    df_removed = pd.DataFrame(removed_records)
    out_removed_csv = STAGED_DIR / "removed_duplicates.csv"
    df_removed.to_csv(out_removed_csv, index=False)
    print(f"Exported Audit Log of Removed Records: {out_removed_csv}")
    
    # Impact Table: Department head-counts and average marks before vs after
    print("\n5. Department Impact Comparison (Before vs After Deduplication):")
    impact_before = df.groupby("department").agg(
        raw_headcount=("student_id", "count"),
        raw_avg_marks=("marks_cleaned", "mean")
    )
    impact_after = df_clean_dedup.groupby("department").agg(
        clean_headcount=("student_id", "count"),
        clean_avg_marks=("marks_cleaned", "mean")
    )
    impact = impact_before.join(impact_after)
    impact["headcount_diff"] = impact["raw_headcount"] - impact["clean_headcount"]
    impact["avg_marks_shift"] = (impact["clean_avg_marks"] - impact["raw_avg_marks"]).round(2)
    print(impact.to_string())
    
    out_staged = STAGED_DIR / "students_stage6_deduplicated.csv"
    df_clean_dedup.to_csv(out_staged, index=False)
    print(f"\nSaved Deduplicated Data to: {out_staged}")
    return df_clean_dedup

if __name__ == "__main__":
    run_deduplication()

