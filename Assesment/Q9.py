import pandas as pd
import os

emp_file = "employees_dept.csv" if os.path.exists("employees_dept.csv") else "employees.csv"
dept_file = "departments.csv"

emp = pd.read_csv(emp_file)
dept = pd.read_csv(dept_file)

merged = pd.merge(emp, dept, on="DeptID")
print("Merged dataset:")
print(merged)
