"""
Task 8: RegEx Matching for Identifying and Cleaning Invalid Data
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
STAGED_DIR = BASE_DIR / "staged"
INPUT_CSV = STAGED_DIR / "students_stage6_deduplicated.csv"

# ---------------------------------------------------------
# Production Regular Expression Specifications
# ---------------------------------------------------------
PATTERNS = {
    "email": r"^[a-zA-Z0-9._%+'-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
    "phone_indian": r"^(?:\+91[-\s]?|0)?[6-9]\d{9}$",
    "student_id": r"^MU\d{2}[A-Z]{3}\d{4}$",
    "pin_code": r"^[1-9]\d{5}$",
    "iso_date": r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$"
}

def run_regex_testing():
    print("=" * 80)
    print("TASK 8: REGEX SPECIFICATION, VALIDATION & BOUNDARY TESTING")
    print("=" * 80)
    
    # 1. 25 Comprehensive Test Cases (8 Valid, 10 Invalid, 7 Boundary Cases)
    test_cases = [
        # Field, Input, Expected Valid?, Category, Description
        ("email", "priya.nair@meridian.edu", True, "VALID", "Standard university institutional email"),
        ("email", "karthik.r@gmail.com", True, "VALID", "Standard commercial email domain"),
        ("email", "john.o'brien@meridian.edu", True, "VALID", "Apostrophe in email local-part"),
        ("email", "student123@sub.meridian.ac.in", True, "VALID", "Multi-level sub-domain and ccTLD"),
        ("email", "anitha.s@@meridian.edu", False, "INVALID", "Double @@ symbol typo"),
        ("email", "irfan.m@gmail", False, "INVALID", "Missing top-level domain (.com/.edu)"),
        ("email", "priya .nair@meridian.edu", False, "INVALID", "Internal whitespace in local part"),
        ("email", "karthik.meridian.edu", False, "INVALID", "Missing @ symbol entirely"),
        ("email", "meena@.com", False, "BOUNDARY", "Missing domain name before dot"),
        ("email", "user@domain..com", False, "BOUNDARY", "Consecutive dots in domain"),
        
        # Phone
        ("phone_indian", "9840012345", True, "VALID", "Standard 10-digit mobile starting with 9"),
        ("phone_indian", "+91-9840012345", True, "VALID", "Prefix +91 with hyphen separator"),
        ("phone_indian", "09444098765", True, "VALID", "Leading trunk zero format"),
        ("phone_indian", "7181803430", True, "VALID", "10-digit mobile starting with 7"),
        ("phone_indian", "(044) 2345 6789", False, "INVALID", "Landline with STD code & brackets"),
        ("phone_indian", "98400", False, "INVALID", "Truncated 5-digit number"),
        ("phone_indian", "5840012345", False, "INVALID", "Starts with 5 (invalid Indian mobile digit)"),
        ("phone_indian", "98400 123456", False, "INVALID", "11 digits without trunk prefix"),
        ("phone_indian", "9840012345.", False, "BOUNDARY", "Trailing period / punctuation"),
        ("phone_indian", "+919840012345", True, "BOUNDARY", "+91 prefix without separator"),
        
        # Student ID
        ("student_id", "MU23CSE0147", True, "VALID", "Valid 2023 CSE student ID"),
        ("student_id", "MU22MEC0098", True, "VALID", "Valid 2022 MEC student ID"),
        ("student_id", "mu23ece0211", False, "INVALID", "Lower-case letters (violates standard)"),
        ("student_id", "MU23CS0147", False, "INVALID", "2-letter department code instead of 3"),
        ("student_id", "MU24ITE030", False, "BOUNDARY", "3-digit serial instead of 4-digit"),
        
        # PIN Code
        ("pin_code", "600001", True, "VALID", "Valid Chennai GPO PIN code"),
        ("pin_code", "060001", False, "INVALID", "Leading zero (illegal in Indian Postal Code)"),
        ("pin_code", "60001", False, "BOUNDARY", "5-digit postal code (incomplete)")
    ]
    
    results = []
    for field, inp, exp, cat, desc in test_cases:
        pat = PATTERNS[field]
        actual = bool(re.match(pat, str(inp)))
        passed = (actual == exp)
        results.append({
            "Field": field,
            "Input Value": str(inp),
            "Category": cat,
            "Expected": exp,
            "Actual": actual,
            "Result": "PASS" if passed else "FAIL",
            "Description": desc
        })
    df_results = pd.DataFrame(results)
    print("\n1. RegEx Test-Case Verification Table (28 Cases Evaluated):")
    print(df_results[["Field", "Input Value", "Category", "Expected", "Actual", "Result"]].to_string(index=False))
    
    # 2. Applying RegEx Validation and Cleaning on the Live Dataset
    df = pd.read_csv(INPUT_CSV, dtype={"phone": str, "student_id": str})
    
    # Format phone as clean 10-digit string
    df["phone_str"] = df["phone"].apply(lambda p: str(p).split(".")[0] if pd.notna(p) and str(p).strip() != "" and str(p).strip() != "nan" else np.nan)
    df["phone_valid"] = df["phone_str"].str.match(r"^[6-9]\d{9}$", na=False)
    bad_phones = (~df["phone_valid"]).sum()
    print(f"Phones failing standard 10-digit regex: {bad_phones}")
    
    # 3. Critical Limitations of RegEx
    print("\n3. Demonstrating Theoretical and Practical Limitations of RegEx:")
    print("A. False Positive (Passes syntax, but functionally invalid):")
    print("   - Value: '9999999999' -> Perfectly matches '^[6-9]\\d{9}$', yet is an obvious dummy/spam number.")
    print("   - Value: 'nobody@meridian.edu' -> Valid email pattern, but mailbox does not exist (SMTP check required).")
    print("B. False Negative (Genuine entity rejected by overly strict pattern):")
    print("   - Value: 'priya+research@meridian.edu' -> Valid RFC 5322 plus-subaddress, rejected if '+' is omitted from pattern.")
    print("   - Value: 'alumni@meridian.technology' -> Genuine 10-letter ICANN new gTLD rejected if pattern limits TLD to '{2,4}'.")

if __name__ == "__main__":
    run_regex_testing()
