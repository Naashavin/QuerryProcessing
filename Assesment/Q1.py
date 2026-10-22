import pandas as pd

df = pd.read_csv("employees.csv")

high_salary = df[df["Salary"] > 50000]
print("Employees earning more than 50000:")
print(high_salary)

avg_salary = df.groupby("Department")["Salary"].mean()
print("\nAverage salary department-wise:")
print(avg_salary)
