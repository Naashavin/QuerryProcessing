# Meridian University Student Information System (SIS)
## Intelligent Data Cleaning & Quality Improvement Pipeline (CO3)
**Author:** Avinaash A  
**Register Number:** 192324260  
**Course:** DSA0501 - Query Processing for Data Science  
**Nature:** Individual Assignment | **Marks:** 50  

---

## 1. Project Overview
This project delivers an end-to-end, reproducible, non-destructive data cleaning and quality engineering pipeline in Python for Meridian University's multi-source Student Information System. The system diagnoses and repairs defects across 11 core attributes over 5,700+ raw records, standardizing formats, resolving departmental synonyms, imputing missing data without destroying variance, purging multi-level duplicates, bounding statistical and domain outliers, and providing verifiable persistence.

---

## 2. Directory Structure
```text
Assignment 3 - CO3/
├── QPDS_A3_192324260_Report.docx  # Comprehensive 30+ page formal engineering report
├── QPDS_A3_192324260_Code.zip     # Clean submission archive with all scripts & datasets
├── diagrams/                      # High-resolution architectural and statistical plots
│   ├── fig1_cleaning_workflow.png
│   ├── fig2_data_profiling_missing_outliers.png
│   ├── fig3_fuzzy_roc_thresholds.png
│   └── fig4_day4_v2_architecture.png
└── code/
    ├── raw/                       # Original raw datasets (cryptographically immutable)
    │   ├── students_dirty.csv     # Primary dataset (5,734 records, seed=42)
    │   ├── students_test.csv      # Generalization test dataset (263 records, seed=101)
    │   └── portal_dirty.csv       # Day-4 Partner Admission Portal (1,135 records, seed=202)
    ├── staged/                    # Intermediate audit logs & review queues
    │   ├── removed_duplicates.csv # Detailed audit log of 322 purged duplicate rows
    │   └── fuzzy_review_queue.csv # 23 human-in-the-loop review cases (Zone 2)
    ├── curated/                   # Production curated datasets & data dictionary
    │   ├── clean_students_output.csv
    │   ├── clean_students_output.json
    │   ├── portal_cleaned_v2.csv
    │   └── data_dictionary.csv
    ├── generate_data.py           # Synthetic data generation & checksum generator
    ├── task1_analysis.py          # Baseline raw queries & prediction formulation
    ├── profile.py                 # Column-by-column profiling & problem taxonomy
    ├── standardize.py             # Name casing, ISO dates, phones, dept consolidation
    ├── missing_handler.py         # MCAR/MAR pattern audit & 4-method imputation bench
    ├── outlier_handler.py         # IQR vs Z-score vs domain bounding [0, 100]
    ├── deduplicator.py            # Exact, key-conflict and partial duplicate merge
    ├── fuzzy_matcher.py           # Difflib/Levenshtein similarity & DOB blocking
    ├── regex_cleaner.py           # Regex patterns & 28-case verification harness
    ├── normalize_save.py          # Min-Max & Z-Score scaling, JSON/CSV persistence
    ├── clean_students.py          # Modular production CLI pipeline (Tasks 1-10)
    ├── evaluate.py                # Before-vs-after quality metrics & prediction check
    ├── clean_students_v2.py       # Day-4 resilient pipeline for partner admission portal
    ├── day4_portal.py             # Day-4 evaluation, failure analysis & regression check
    ├── test_suite.py              # 18-case automated unit test suite
    └── generate_plots.py          # Matplotlib diagram generator
```

---

## 3. Cryptographic Verification (SHA-256 Checksums)
| Dataset File | Records | Size | SHA-256 Checksum |
|---|---|---|---|
| `raw/students_dirty.csv` | 5,734 | 480 KB | `a9e3c0cae014a2fdfc472118f76adbc9b410d67f2084d6a80229b7dba862e1ad` |
| `raw/students_test.csv` | 263 | 22 KB | `26344f94b296fcbc7ec26d3ce7f53025555dcc3cb11679d779c8bbb4214e4ae0` |
| `raw/portal_dirty.csv` | 1,135 | 98 KB | `fa73aaeb6070bbb7c6ea17fc3fb327c0a6012064ea710e7ae6e56709384ee454` |
| `curated/clean_students_output.csv` | 5,412 | 1,101 KB | `8e7850bb628ff3da2cb7504269cb8cfa89c28f64b2c1b19d33013ee0b90c17ea` |

---

## 4. How to Run the Pipeline

### Step 1: Execute Automated Unit Test Suite
```powershell
python code/test_suite.py
```
*Expected: 18 unit tests ran in 0.002s (OK)*

### Step 2: Run Production CLI Pipeline on Primary Data
```powershell
python code/clean_students.py --input "raw/students_dirty.csv" --output "curated/clean_students_output.csv"
```

### Step 3: Run Validation Test on New Cohort
```powershell
python code/clean_students.py --input "raw/students_test.csv" --output "curated/test_cleaned_output.csv"
```

### Step 4: Run Day-4 Admission Portal Pipeline (V2)
```powershell
python code/clean_students_v2.py --input "raw/portal_dirty.csv" --output "curated/portal_cleaned_v2.csv"
```

### Step 5: Evaluate Quality Metrics & Re-run Baseline Predictions
```powershell
python code/evaluate.py
```

---

## 5. Summary of Engineering Achievements
1. **100% Elimination of Impossible Outliers:** Corrected 198 marks outliers (including typo extra zeros 640->64, 850->85) and 208 attendance percentage outliers (>100% and negative values).
2. **5.62% Duplicate Purge:** Removed 120 exact duplicates, 95 key conflicts, and 107 partial name+DOB duplicates with zero data loss using priority survivorship rules.
3. **93.1% Department Synonyms Consolidated:** Collapsed 87 disparate textual representations into 6 accredited canonical academic departments.
4. **99.96% Reduction in Comparison Space:** Implemented Date-of-Birth blocking in fuzzy entity resolution, reducing $14.6\text{M}$ pairs down to $5,624$ pairs ($2,603\times$ speedup).
5. **Zero Regression on Day-4 Challenge:** Designed `clean_students_v2.py` capable of ingesting partner admission portals (timestamps, honorifics, fractional marks) while proving bit-for-bit backward compatibility on legacy files.

