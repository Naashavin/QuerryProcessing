import pandas as pd

df = pd.read_csv("customer_dataset.csv")

duplicates = df[df.duplicated()]
print("Duplicate records:")
print(duplicates)

clean_df = df.drop_duplicates()

print("\nUpdated dataset:")
print(clean_df)
