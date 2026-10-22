import pandas as pd

df = pd.read_csv("employees_validation.csv")

invalid_names = df["Name"].isna() | (df["Name"].str.strip() == "")
invalid_ages = (df["Age"] < 18) | (df["Age"] > 65)
invalid_salaries = df["Salary"] <= 0

invalid_mask = invalid_names | invalid_ages | invalid_salaries

print("Invalid records:")
print(df[invalid_mask])

clean_df = df[~invalid_mask]
print("\nCleaned records:")
print(clean_df)

print("\n--- Validation Report ---")
print("Total records:", len(df))
print("Valid records:", len(clean_df))
print("Invalid records removed:", len(df[invalid_mask]))
