import pandas as pd
import os

emp_file = "employee_multi.csv" if os.path.exists("employee_multi.csv") else "table_employee.csv"
dept_file = "department_multi.csv" if os.path.exists("department_multi.csv") else "table_department.csv"
sal_file = "salary_multi.csv" if os.path.exists("salary_multi.csv") else "table_salary.csv"

emp = pd.read_csv(emp_file)
dept = pd.read_csv(dept_file)
sal = pd.read_csv(sal_file)

merged = emp.merge(dept, on="DeptID").merge(sal, on="EmpID")
dept_col = "Department" if "Department" in merged.columns else "DeptName"

print("Merged table:")
print(merged)

dept_avg = merged.groupby(dept_col)["Salary"].transform("mean")
above_avg = merged[merged["Salary"] > dept_avg]
print("\nEmployees earning above department average:")
print(above_avg)

dept_max = merged.groupby(dept_col)["Salary"].max()
print("\nDepartment-wise highest salary:")
print(dept_max)
