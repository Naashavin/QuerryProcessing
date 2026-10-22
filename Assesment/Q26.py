import pandas as pd

df = pd.read_csv("employees_str_types.csv")

df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
df["Salary"] = pd.to_numeric(df["Salary"], errors="coerce")

df = df.dropna()

print("Cleaned numeric dataset:")
print(df)

avg_salary = df["Salary"].mean()
print("\nAverage salary:", avg_salary)
