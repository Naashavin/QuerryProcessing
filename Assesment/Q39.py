import glob
import os
import pandas as pd

folder = "ecommerce_folder" if os.path.exists("ecommerce_folder") else "ecommerce_batches"
files = glob.glob(f"{folder}/*.csv")

dfs = [pd.read_csv(f) for f in files]
df = pd.concat(dfs, ignore_index=True)

df = df.drop_duplicates()
df = df.dropna()

df["OrderDate"] = pd.to_datetime(df["OrderDate"])
df["TotalPrice"] = df["Quantity"] * df["Price"]

print("Master dataset:")
print(df)

top_product = df.groupby("Product")["Quantity"].sum().idxmax()
print("\nTop-selling product:", top_product)

df.to_csv("master_ecommerce.csv", index=False)
