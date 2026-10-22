import pandas as pd

df = pd.read_csv("sales_data.csv")

sorted_df = df.sort_values(by="SalesAmount", ascending=False)

print("Top 10 highest-selling products:")
print(sorted_df.head(10))
