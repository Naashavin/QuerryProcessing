import pandas as pd

df = pd.read_csv("employees_inconsistent.csv")

df["Department"] = df["Department"].replace(["I.T", "Information Technology", "info tech"], "IT")

print("Standardized dataset:")
print(df)

print("\nEmployee count in each department:")
print(df["Department"].value_counts())
