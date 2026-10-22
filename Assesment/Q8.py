import pandas as pd

df = pd.read_csv("employees.csv")

result = df.groupby("Department")["Salary"].agg(["sum", "mean", "count"])
print("Department summary:")
print(result)
