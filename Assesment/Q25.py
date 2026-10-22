import pandas as pd

df = pd.read_csv("customers_dirty_strings.csv")

df["Name"] = df["Name"].str.strip().str.replace(r"\s+", " ", regex=True).str.title()

pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
df["Valid_Email"] = df["Email"].str.match(pattern)

print("Cleaned data:")
print(df)

invalid_records = df[df["Valid_Email"] == False]
print("\nInvalid records:")
print(invalid_records)
