import pandas as pd

student = pd.read_csv("students_table.csv")
department = pd.read_csv("departments_table.csv")

merged = pd.merge(student, department, on="DeptID")
result = merged[["Name", "Department"]]

print("Student Name and Department:")
print(result)
