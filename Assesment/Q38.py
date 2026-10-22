import pandas as pd

df = pd.read_csv("sales.csv")

print("Mean:")
print(df[["Quantity", "Sales"]].mean())

print("\nMedian:")
print(df[["Quantity", "Sales"]].median())

print("\nMode:")
print(df[["Quantity", "Sales"]].mode().iloc[0])

print("\nStandard Deviation:")
print(df[["Quantity", "Sales"]].std())

print("\nVariance:")
print(df[["Quantity", "Sales"]].var())

correlation = df["Quantity"].corr(df["Sales"])
print("\nCorrelation between Quantity and Sales:", correlation)
