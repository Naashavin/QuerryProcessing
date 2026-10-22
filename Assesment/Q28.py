import pandas as pd
import os

file_name = "healthcare.csv" if os.path.exists("healthcare.csv") else "healthcare_data.csv"
df = pd.read_csv(file_name)

missing_count = df.isnull().sum()
print("Missing values count:")
print(missing_count)

missing_percent = (df.isnull().sum() / len(df)) * 100
print("\nPercentage of missing values:")
print(missing_percent)

df = df.fillna(df.mean(numeric_only=True))
print("\nCleaned dataset:")
print(df)
