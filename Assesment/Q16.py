import pandas as pd

df = pd.read_xml("library.xml", parser="etree")

print("Total books:", len(df))

print("\nBooks written after 2020:")
print(df[df["year"] > 2020])

print("\nBooks costing more than 500:")
print(df[df["price"] > 500])
