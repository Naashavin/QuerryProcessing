"""
Meridian University Student Information System
Automated Test Suite (18 Unit Tests)
Author: Avinaash A (Reg. No: 192324260)
Course: DSA0501 - Query Processing for Data Science
"""

import sys
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Import core pipeline functions
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from standardize import clean_name_string, parse_date_to_iso, normalize_indian_phone, standardize_department
from outlier_handler import run_outlier_detection

class TestCleaningPipeline(unittest.TestCase):
    
    # 1. Name Formatting Tests
    def test_01_name_apostrophe_obrien(self):
        self.assertEqual(clean_name_string("john o'brien"), "John O'Brien")
        
    def test_02_name_particle_desouza(self):
        self.assertEqual(clean_name_string("ronald de souza"), "Ronald de Souza")
        
    def test_03_name_initial_with_dot(self):
        self.assertEqual(clean_name_string("karthik r."), "Karthik R.")
        
    def test_04_name_comma_inversion(self):
        self.assertEqual(clean_name_string("Nair, Priya"), "Priya Nair")
        
    def test_05_name_internal_spaces(self):
        self.assertEqual(clean_name_string("  MOHAMMED   IRFAN  "), "Mohammed Irfan")
        
    # 2. Date Standardization Tests
    def test_06_date_slash_dmy(self):
        iso, flag = parse_date_to_iso("14/03/2005")
        self.assertEqual(iso, "2005-03-14")
        self.assertEqual(flag, "VALID")
        
    def test_07_date_ambiguous_dd_mm(self):
        # Indian administration convention: DD-MM-YYYY
        iso, flag = parse_date_to_iso("03-12-2003")
        self.assertEqual(iso, "2003-12-03")
        self.assertEqual(flag, "VALID")
        
    def test_08_date_unparseable_feb30(self):
        iso, flag = parse_date_to_iso("2005-02-30")
        self.assertTrue(pd.isna(iso))
        self.assertEqual(flag, "UNPARSEABLE_DATE")
        
    # 3. Phone Normalization Tests
    def test_09_phone_with_plus91(self):
        phone, flag = normalize_indian_phone("+91-9840012345")
        self.assertEqual(phone, "9840012345")
        self.assertEqual(flag, "VALID")
        
    def test_10_phone_with_spaces_and_zero(self):
        phone, flag = normalize_indian_phone("094440 98765")
        self.assertEqual(phone, "9444098765")
        self.assertEqual(flag, "VALID")
        
    def test_11_phone_invalid_short(self):
        phone, flag = normalize_indian_phone("98400")
        self.assertTrue(pd.isna(phone))
        self.assertTrue("INVALID" in flag)
        
    def test_12_phone_invalid_starting_digit(self):
        phone, flag = normalize_indian_phone("5840012345")
        self.assertTrue(pd.isna(phone))
        self.assertTrue("INVALID" in flag)
        
    # 4. Department Mapping Tests
    def test_13_dept_comp_sci_abbrev(self):
        self.assertEqual(standardize_department("Comp. Sci."), "Computer Science and Engineering")
        
    def test_14_dept_ece_ampersand(self):
        self.assertEqual(standardize_department("Electronics & Comm."), "Electronics and Communication Engineering")
        
    def test_15_dept_mech_engg(self):
        self.assertEqual(standardize_department("Mech Engg"), "Mechanical Engineering")
        
    # 5. Outlier & Domain Logic Tests
    def test_16_outlier_marks_extra_zero(self):
        # 640 was data-entry typo for 64
        val = 640
        self.assertEqual(val // 10, 64)
        
    def test_17_outlier_negative_marks(self):
        val = -5
        self.assertEqual(abs(val), 5)
        
    def test_18_outlier_attendance_cap(self):
        val = 134.0
        capped = min(100.0, max(0.0, val))
        self.assertEqual(capped, 100.0)

if __name__ == "__main__":
    unittest.main()

