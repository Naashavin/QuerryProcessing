import pandas as pd

df = pd.read_json("employee.json")

filtered = df[(df["Salary"] > 60000) & (df["Department"] == "IT")]
print("Employees with Salary > 60000 and Department = IT:")
print(filtered)
