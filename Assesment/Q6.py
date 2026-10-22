import pandas as pd
import os

file_name = "products.csv" if os.path.exists("products.csv") else "products_usd.csv"
df = pd.read_csv(file_name)

df["Price_INR"] = df["Price_USD"] * 83

print("Updated dataset with Price_INR:")
print(df)
