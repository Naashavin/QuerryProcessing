"""
Meridian University Student Information System
Data Generator for Assignment 3 (CO3)
Author: Avinaash A (Reg. No: 192324260)
Course: DSA0501 - Query Processing for Data Science

Generates:
1. raw/students_dirty.csv (>= 5000 rows, seed=42)
2. raw/students_test.csv  (>= 200 rows,  seed=101)
3. raw/portal_dirty.csv   (>= 1000 rows, seed=202)
Calculates and records SHA-256 checksums.
"""

import os
import sys
import random
import hashlib
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# Reference Pools & Domain Definitions
# ---------------------------------------------------------
FIRST_NAMES = [
    "Priya", "Mohammed", "Karthik", "Anitha", "Meena", "Suresh", "Divya", "Aarav",
    "Rajesh", "Sneha", "Vignesh", "Lakshmi", "Ashwin", "Deepa", "Rahul", "Swetha",
    "Vijay", "Kavitha", "Manoj", "Keerthi", "Arun", "Bhavna", "Chirag", "Farhan",
    "Gita", "Harish", "Ishwarya", "Jagan", "Naveen", "Pavithra", "Revathi", "Sanjay",
    "Tarun", "Uma", "Varun", "Yamini", "Zeeshan", "Abishek", "Charulatha", "Dinesh",
    "Ezhil", "Gayathri", "Hemalatha", "Indumathi", "Jayanth", "Lavanya", "Monika",
    "Nithya", "Pradeep", "Rohit", "Sandhya", "Subramanian", "Tharani", "Vasanth"
]

LAST_NAMES = [
    "Nair", "Irfan", "Kumar", "S", "K", "R", "Rao", "Sharma", "Menon", "Reddy",
    "Balaji", "Sundaram", "Venkatesh", "Murugan", "Nathan", "Pillai", "Iyer",
    "Iyengar", "Patel", "Singh", "Das", "Gupta", "Joshi", "Verma", "de Souza",
    "O'Brien", "Fernandez", "Pereira", "D'Silva", "Choudhury", "Bose", "Banerjee"
]

CITIES = [
    "Chennai", "Madurai", "Coimbatore", "Salem", "Trichy", "Tirunelveli",
    "Vellore", "Erode", "Thanjavur", "Kanchipuram", "Bengaluru", "Hyderabad",
    "Kochi", "Trivandrum", "Mysuru"
]

CANONICAL_DEPARTMENTS = {
    "Computer Science and Engineering": [
        "Computer Science", "CSE", "Comp. Sci.", "Comp Sci & Engg",
        "computer science ", "CS", "Computer Science & Engineering", "comp sci"
    ],
    "Information Technology": [
        "Info Tech", "IT", "Information Tech", "Infotech",
        "information technology", "I.T.", "IT Dept"
    ],
    "Electronics and Communication Engineering": [
        "Electronics & Comm.", "ECE", "Electronics and Comm", "E.C.E.",
        "Electronics", "ece", "Electronics & Comm Engg"
    ],
    "Mechanical Engineering": [
        "Mech Engg", "MECH", "Mechanical", "Mech. Engineering",
        "Mech", "mechanical", "Mechanical Eng."
    ],
    "Civil Engineering": [
        "CIVIL", "Civil Engg", "Civ. Engg.", "Civil",
        "civil engineering", "C.E.", "Civil Dept"
    ],
    "Business Administration": [
        "MBA", "Business Admin", "Mgmt Studies", "Management",
        "BBA", "business administration", "Business Management"
    ]
}

DEPT_CODES = {
    "Computer Science and Engineering": "CSE",
    "Information Technology": "ITE",
    "Electronics and Communication Engineering": "ECE",
    "Mechanical Engineering": "MEC",
    "Civil Engineering": "CIV",
    "Business Administration": "BAD"
}

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def sha256_file(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def random_date_str(rng: random.Random, start_year=2002, end_year=2006) -> tuple:
    """Returns (iso_str, dirty_str)"""
    y = rng.randint(start_year, end_year)
    m = rng.randint(1, 12)
    d = rng.randint(1, 28)
    iso_date = f"{y:04d}-{m:02d}-{d:02d}"
    
    # format varieties
    fmt = rng.choice(["iso", "slash_dmy", "hyphen_dmy", "mon_dmy", "slash_ymd", "ambiguous", "invalid"])
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    if fmt == "iso":
        return iso_date, iso_date
    elif fmt == "slash_dmy":
        return iso_date, f"{d:02d}/{m:02d}/{y:04d}"
    elif fmt == "hyphen_dmy":
        return iso_date, f"{d:02d}-{m:02d}-{y:04d}"
    elif fmt == "mon_dmy":
        return iso_date, f"{d:02d}-{months[m-1]}-{y:04d}"
    elif fmt == "slash_ymd":
        return iso_date, f"{y:04d}/{m:02d}/{d:02d}"
    elif fmt == "ambiguous":
        # e.g. 03-12-2003
        day_amb = rng.randint(1, 12)
        mon_amb = rng.randint(1, 12)
        return f"{y:04d}-{mon_amb:02d}-{day_amb:02d}", f"{day_amb:02d}-{mon_amb:02d}-{y:04d}"
    else: # invalid date
        return iso_date, "2005-02-30"

def make_dirty_phone(rng: random.Random, clean_num: str) -> str:
    style = rng.choice(["plain", "space", "hyphen", "plus91", "zero", "landline", "short"])
    if style == "plain":
        return clean_num
    elif style == "space":
        return f"{clean_num[:5]} {clean_num[5:]}"
    elif style == "hyphen":
        return f"{clean_num[:5]}-{clean_num[5:]}"
    elif style == "plus91":
        return f"+91-{clean_num}"
    elif style == "zero":
        return f"0{clean_num}"
    elif style == "landline":
        return f"(044) {clean_num[2:6]} {clean_num[6:]}"
    else:
        return clean_num[:5] # short/truncated invalid

def make_dirty_email(rng: random.Random, clean_email: str) -> str:
    variant = rng.choice(["ok", "double_at", "missing_domain", "spaces", "missing_at"])
    if variant == "ok":
        return clean_email
    elif variant == "double_at":
        return clean_email.replace("@", "@@")
    elif variant == "missing_domain":
        return clean_email.split("@")[0] + "@gmail"
    elif variant == "spaces":
        parts = clean_email.split("@")
        return f"{parts[0]} @{parts[1]}"
    else:
        return clean_email.replace("@", ".")

def make_dirty_name(rng: random.Random, first: str, last: str) -> str:
    style = rng.choice(["standard", "leading_trailing", "double_space", "upper", "lower", "comma"])
    full = f"{first} {last}"
    if style == "standard":
        return full
    elif style == "leading_trailing":
        return f"  {full}  "
    elif style == "double_space":
        return f"{first}  {last}"
    elif style == "upper":
        return full.upper()
    elif style == "lower":
        return full.lower()
    elif style == "comma":
        return f"{last}, {first}"
    return full

# ---------------------------------------------------------
# Generator 1: Primary Dirty Dataset (students_dirty.csv)
# ---------------------------------------------------------
def generate_students_dirty(num_records=5200, seed=42):
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    
    records = []
    student_counter = 100
    
    # 1. Base clean templates
    base_pool = []
    dept_names = list(CANONICAL_DEPARTMENTS.keys())
    
    for i in range(num_records):
        adm_year = rng.choice([2021, 2022, 2023, 2024])
        dept_canonical = rng.choice(dept_names)
        dept_code = DEPT_CODES[dept_canonical]
        student_id = f"MU{str(adm_year)[2:]}{dept_code}{student_counter:04d}"
        student_counter += 1
        
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        full_name = f"{first} {last}"
        
        gender = rng.choice(["Female", "Male"])
        dob_iso, _ = random_date_str(rng, 2002, 2006)
        
        # Indian phone 10 digits starting 6-9
        first_digit = rng.choice(["6", "7", "8", "9"])
        clean_phone = first_digit + "".join(str(rng.randint(0, 9)) for _ in range(9))
        
        f_clean = first.lower().replace("'", "").replace(" ", "")
        l_clean = last.lower().replace("'", "").replace(" ", "")
        email_user = f"{f_clean}.{l_clean}"
        clean_email = f"{email_user}@meridian.edu"
        city = rng.choice(CITIES)
        
        # Admission date: July/August of admission year
        adm_month = rng.choice([7, 8])
        adm_day = rng.randint(1, 25)
        adm_date_iso = f"{adm_year:04d}-{adm_month:02d}-{adm_day:02d}"
        
        # Normal distributions
        attendance = round(float(np.clip(np_rng.normal(82.0, 10.0), 45.0, 99.0)), 1)
        marks = int(np.clip(np_rng.normal(74.0, 12.0), 35, 98))
        
        base_pool.append({
            "student_id": student_id,
            "full_name": full_name,
            "dob": dob_iso,
            "gender": gender,
            "department": dept_canonical,
            "email": clean_email,
            "phone": clean_phone,
            "city": city,
            "admission_date": adm_date_iso,
            "attendance_pct": attendance,
            "marks": marks
        })
    
    # 2. Inject Defective & Dirty Variations
    placeholders = ["NA", "-", "?", "null", "N/A", ""]
    
    for idx, item in enumerate(base_pool):
        rec = dict(item)
        
        # A. Whitespace & Casing in Names
        parts = rec["full_name"].split(" ", 1)
        f_part = parts[0]
        l_part = parts[1] if len(parts) > 1 else "K"
        rec["full_name"] = make_dirty_name(rng, f_part, l_part)
        
        # B. ID lowercasing
        if rng.random() < 0.12:
            rec["student_id"] = rec["student_id"].lower()
            
        # C. DOB dirty formatting & missingness
        if rng.random() < 0.09: # 9% missing
            rec["dob"] = rng.choice(placeholders)
        else:
            _, dirty_dob = random_date_str(rng)
            rec["dob"] = dirty_dob
            
        # D. Gender representation
        if rng.random() < 0.04:
            rec["gender"] = rng.choice(["-", "unknown", ""])
        else:
            g = rec["gender"]
            if g == "Female":
                rec["gender"] = rng.choice(["F", "Female", "FEMALE", "female", "f"])
            else:
                rec["gender"] = rng.choice(["M", "Male", "MALE", "male", "m"])
                
        # E. Department variants
        dept_canonical = rec["department"]
        variant_list = CANONICAL_DEPARTMENTS[dept_canonical]
        rec["department"] = rng.choice(variant_list)
        if rng.random() < 0.10:
            rec["department"] = f"  {rec['department']}  "
            
        # F. Email defects
        if rng.random() < 0.04: # 4% invalid
            rec["email"] = make_dirty_email(rng, rec["email"])
            
        # G. Phone defects & missingness
        if rng.random() < 0.085: # 8.5% missing
            rec["phone"] = rng.choice(placeholders)
        else:
            rec["phone"] = make_dirty_phone(rng, rec["phone"])
            
        # H. City casing & whitespace
        if rng.random() < 0.15:
            rec["city"] = rec["city"].lower()
        elif rng.random() < 0.08:
            rec["city"] = f"  {rec['city']} "
            
        # I. Admission date formatting
        if rng.random() < 0.03:
            rec["admission_date"] = rng.choice(placeholders)
        else:
            _, d_adm = random_date_str(rng, 2021, 2024)
            rec["admission_date"] = d_adm
            
        # J. Attendance missingness & impossible outliers
        att_dice = rng.random()
        if att_dice < 0.085: # 8.5% missing
            rec["attendance_pct"] = rng.choice(placeholders)
        elif att_dice < 0.12: # impossible outliers (>100% or <0)
            rec["attendance_pct"] = rng.choice([134.0, 115.5, 102.0, -8.0, 145.0])
            
        # K. Marks missingness & extreme outliers
        m_dice = rng.random()
        if m_dice < 0.085: # 8.5% missing
            rec["marks"] = rng.choice(placeholders)
        elif m_dice < 0.125: # extreme outliers (>100 or <0)
            rec["marks"] = rng.choice([640, -5, 580, -10, 850, 105])
            
        records.append(rec)
        
    # 3. Inject Explicit Duplicates (>= 5% total)
    # - Exact duplicates: >= 2% (105 records)
    exact_dup_indices = rng.sample(range(len(records)), 120)
    for i in exact_dup_indices:
        records.append(dict(records[i]))
        
    # - Conflicting duplicates: >= 1% (55 records)
    conflict_indices = rng.sample(range(len(records)), 65)
    for i in conflict_indices:
        dup_rec = dict(records[i])
        dup_rec["phone"] = "98400 99999"
        dup_rec["marks"] = 92
        records.append(dup_rec)
        
    # - Partial duplicates: >= 2% (110 records)
    # same name + dob under different student_id
    partial_indices = rng.sample(range(len(records)), 125)
    for i in partial_indices:
        p_rec = dict(records[i])
        new_id = f"MU24CSE{rng.randint(9000, 9999)}"
        p_rec["student_id"] = new_id
        records.append(p_rec)
        
    # 4. Inject Similar-but-Different Name Pairs (>= 100 pairs)
    fuzzy_name_pairs = [
        ("Karthik R", "Karthick R"),
        ("Anitha S", "Anita S"),
        ("Mohammed Irfan", "Mohd Irfan"),
        ("Vikas S", "Vikash S"),
        ("Pooja M", "Puja M"),
        ("Deepa K", "Dheepa K"),
        ("Suresh Babu", "Suresh Baboo"),
        ("Ashwin Kumar", "Ashwin Kumaar"),
        ("Swetha R", "Sweta R"),
        ("Naveen Chandran", "Navin Chandran"),
        ("Yamini S", "Yaamini S"),
        ("Meena K", "Meena, K"),
        ("John O'Brien", "John Obrien"),
        ("Ronald de Souza", "Ronald De Souza")
    ]
    for _ in range(8): # repeats variants to exceed 100 pairs
        for n1, n2 in fuzzy_name_pairs:
            dob_iso, _ = random_date_str(rng)
            cid = f"MU23ECE{rng.randint(8000, 8999)}"
            records.append({
                "student_id": cid,
                "full_name": n1,
                "dob": dob_iso,
                "gender": "Male",
                "department": "ECE",
                "email": f"test.{rng.randint(100, 999)}@meridian.edu",
                "phone": "9840012345",
                "city": "Chennai",
                "admission_date": "2023-07-10",
                "attendance_pct": 85.0,
                "marks": 78
            })
            records.append({
                "student_id": f"MU23ECE{rng.randint(8000, 8999)}",
                "full_name": n2,
                "dob": dob_iso,
                "gender": "Male",
                "department": "Electronics and Communication Engineering",
                "email": f"test.{rng.randint(100, 999)}@meridian.edu",
                "phone": "98400 12345",
                "city": "Chennai",
                "admission_date": "2023-07-10",
                "attendance_pct": 85.0,
                "marks": 78
            })

    rng.shuffle(records)
    df = pd.DataFrame(records)
    out_path = RAW_DIR / "students_dirty.csv"
    df.to_csv(out_path, index=False)
    chk = sha256_file(out_path)
    print(f"Generated students_dirty.csv: {len(df)} rows, {len(df.columns)} columns.")
    print(f"SHA-256 Checksum: {chk}")
    return out_path, chk

# ---------------------------------------------------------
# Generator 2: Validation Test Dataset (students_test.csv)
# ---------------------------------------------------------
def generate_students_test(num_records=260, seed=101):
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    records = []
    
    dept_names = list(CANONICAL_DEPARTMENTS.keys())
    
    for i in range(num_records):
        adm_year = rng.choice([2021, 2022, 2023, 2024])
        dept_canonical = rng.choice(dept_names)
        dept_code = DEPT_CODES[dept_canonical]
        student_id = f"MU{str(adm_year)[2:]}{dept_code}{7000+i:04d}"
        
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        full_name = f"{first} {last}"
        
        dob_iso, dirty_dob = random_date_str(rng)
        clean_phone = rng.choice(["6", "7", "8", "9"]) + "".join(str(rng.randint(0, 9)) for _ in range(9))
        email = f"{first.lower()}.{last.lower()}@meridian.edu"
        
        att = round(float(np.clip(np_rng.normal(80.0, 10.0), 50.0, 98.0)), 1)
        marks = int(np.clip(np_rng.normal(72.0, 14.0), 40, 95))
        
        # inject occasional flaws
        if rng.random() < 0.10:
            full_name = f"  {full_name.lower()}  "
        if rng.random() < 0.08:
            dept_variant = rng.choice(CANONICAL_DEPARTMENTS[dept_canonical])
        else:
            dept_variant = dept_canonical
        if rng.random() < 0.08:
            marks = rng.choice([550, -15, 120])
        if rng.random() < 0.08:
            att = rng.choice([125.0, -5.0])
        if rng.random() < 0.08:
            dirty_dob = "N/A"
            
        records.append({
            "student_id": student_id,
            "full_name": full_name,
            "dob": dirty_dob,
            "gender": rng.choice(["M", "Female", "MALE", "F"]),
            "department": dept_variant,
            "email": email,
            "phone": make_dirty_phone(rng, clean_phone),
            "city": rng.choice(CITIES),
            "admission_date": f"{adm_year}-08-01",
            "attendance_pct": att,
            "marks": marks
        })
        
    # Edge Cases specified in Task 10:
    # 1. Unknown department
    records.append({
        "student_id": "MU24AER0999", "full_name": "Kavitha R", "dob": "2005-04-12",
        "gender": "Female", "department": "Aeronautical Engineering", "email": "kavitha.r@meridian.edu",
        "phone": "9840012345", "city": "Chennai", "admission_date": "2024-08-01", "attendance_pct": 82.0, "marks": 75
    })
    # 2. Extreme whitespace & casing
    records.append({
        "student_id": "mu24cse1111", "full_name": "   john   o'brien   ", "dob": "12/05/2004",
        "gender": "male", "department": "   computer science   ", "email": "john.obrien@meridian.edu",
        "phone": "+91-9840012345", "city": "chennai", "admission_date": "01-Aug-2024", "attendance_pct": 90.0, "marks": 88
    })
    # 3. Missing values across 4 columns
    records.append({
        "student_id": "MU23BAD0888", "full_name": "Suresh Kumar", "dob": "-",
        "gender": "-", "department": "MBA", "email": "suresh.kumar@meridian.edu",
        "phone": "NA", "city": "Madurai", "admission_date": "2023-07-15", "attendance_pct": "NA", "marks": "?"
    })
    
    df = pd.DataFrame(records)
    out_path = RAW_DIR / "students_test.csv"
    df.to_csv(out_path, index=False)
    chk = sha256_file(out_path)
    print(f"Generated students_test.csv: {len(df)} rows, {len(df.columns)} columns.")
    print(f"SHA-256 Checksum: {chk}")
    return out_path, chk

# ---------------------------------------------------------
# Generator 3: Day-4 Online Admission Portal (portal_dirty.csv)
# ---------------------------------------------------------
def generate_portal_dirty(num_records=1100, seed=202):
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    
    # Layout: applicant_ref,applicant_name,dob,sex,programme,email,mobile,category,hsc_percentage,submitted_on
    programmes = [
        "AI&DS", "Artificial Intell & Data Sci", "Biomedical", "Biomedical Engg",
        "C.S.E.", "Comp Sci & Engg", "Information Technology", "Mechanical",
        "Civil", "Business Administration"
    ]
    categories = ["GEN", "OBC", "SC", "ST", "EWS"]
    honorifics = ["Mr. ", "Ms. ", "Mrs. ", "Dr. ", ""]
    
    records = []
    for i in range(num_records):
        ref = f"AP26-{10000+i:05d}"
        hon = rng.choice(honorifics)
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        
        # Name format varieties: honorific, reversed, initials
        n_style = rng.choice(["hon", "rev", "initial", "std"])
        if n_style == "hon":
            name = f"{hon}{first} {last}"
        elif n_style == "rev":
            name = f"{last} {first}"
        elif n_style == "initial":
            name = f"{first[0]}. {last}"
        else:
            name = f"{first} {last}"
            
        # DOB with dots or text months
        y = rng.randint(2004, 2007)
        m = rng.randint(1, 12)
        d = rng.randint(1, 28)
        months_str = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        dob_style = rng.choice(["dot", "text_mon", "iso", "missing", "impossible"])
        if dob_style == "dot":
            dob = f"{d:02d}.{m:02d}.{y:04d}"
        elif dob_style == "text_mon":
            dob = f"{d:02d} {months_str[m-1]} {y:04d}"
        elif dob_style == "iso":
            dob = f"{y:04d}-{m:02d}-{d:02d}"
        elif dob_style == "impossible":
            dob = "2012-02-30" # impossible leap day / underage
        else:
            dob = rng.choice(["N.A.", "", "Not Provided"])
            
        sex = rng.choice(["Male", "Female", "M", "F", "Prefer not to say"])
        programme = rng.choice(programmes)
        category = rng.choice(categories)
        
        # mobile formats
        raw_num = rng.choice(["6", "7", "8", "9"]) + "".join(str(rng.randint(0, 9)) for _ in range(9))
        p_style = rng.choice(["plus91_hyphen", "zero_space", "landline", "missing", "std"])
        if p_style == "plus91_hyphen":
            mobile = f"+91 {raw_num[:5]}-{raw_num[5:]}"
        elif p_style == "zero_space":
            mobile = f"0{raw_num[:5]} {raw_num[5:]}"
        elif p_style == "landline":
            mobile = f"(0422) {raw_num[2:5]} {raw_num[5:]}"
        elif p_style == "missing":
            mobile = "N.A."
        else:
            mobile = raw_num
            
        email = f"{first.lower()}.{last.lower()}@mailbox.in"
        if rng.random() < 0.05:
            email = email.split("@")[0] + "@mailbox" # missing tld
            
        # marks / hsc_percentage
        m_style = rng.choice(["fraction", "normal", "outlier", "missing"])
        if m_style == "fraction":
            hsc = round(rng.uniform(0.65, 0.98), 2) # e.g. 0.87
        elif m_style == "outlier":
            hsc = rng.choice([455, 620, -10]) # e.g. 455 marks out of 500
        elif m_style == "missing":
            hsc = "N.A."
        else:
            hsc = round(float(np.clip(np_rng.normal(84.0, 8.0), 55.0, 99.5)), 1)
            
        # submitted_on timestamps
        sub_day = rng.randint(15, 25)
        sub_hr = rng.randint(8, 19)
        sub_min = rng.randint(10, 59)
        ts_style = rng.choice(["ts_dot", "ts_text", "date_only"])
        if ts_style == "ts_dot":
            sub_on = f"{sub_day:02d}.07.2026 {sub_hr:02d}:{sub_min:02d}"
        elif ts_style == "ts_text":
            sub_on = f"{sub_day} Jul 2026"
        else:
            sub_on = f"2026-07-{sub_day:02d}"
            
        records.append({
            "applicant_ref": ref,
            "applicant_name": name,
            "dob": dob,
            "sex": sex,
            "programme": programme,
            "email": email,
            "mobile": mobile,
            "category": category,
            "hsc_percentage": hsc,
            "submitted_on": sub_on
        })
        
    # Inject Portal Conflicting Duplicates
    for k in range(35):
        dup = dict(records[k * 15])
        dup["mobile"] = "098400 12399"
        dup["hsc_percentage"] = 0.87
        dup["submitted_on"] = "22.07.2026 09:05"
        records.append(dup)
        
    df = pd.DataFrame(records)
    out_path = RAW_DIR / "portal_dirty.csv"
    df.to_csv(out_path, index=False)
    chk = sha256_file(out_path)
    print(f"Generated portal_dirty.csv: {len(df)} rows, {len(df.columns)} columns.")
    print(f"SHA-256 Checksum: {chk}")
    return out_path, chk

if __name__ == "__main__":
    print("=== Generating Datasets for Assignment 3 (CO3) ===")
    generate_students_dirty(5200, 42)
    generate_students_test(260, 101)
    generate_portal_dirty(1100, 202)
    print("=== All Datasets Generated Successfully ===")
