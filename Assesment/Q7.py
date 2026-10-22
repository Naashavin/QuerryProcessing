import pandas as pd

df = pd.read_csv("monthly_sales.csv")

total = df["Sales"].sum()
average = df["Sales"].mean()
maximum = df["Sales"].max()
minimum = df["Sales"].min()

print("Total sales:", total)
print("Average sales:", average)
print("Maximum sales:", maximum)
print("Minimum sales:", minimum)
