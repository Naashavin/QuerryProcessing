import pandas as pd

df = pd.read_csv("online_retail.csv")

print("Duplicate rows:")
print(df[df.duplicated()])

df = df.drop_duplicates()

print("\nMissing values in CustomerID:", df["CustomerID"].isnull().sum())
df = df.dropna(subset=["CustomerID"])

print("\nCleaned dataset:")
print(df)
