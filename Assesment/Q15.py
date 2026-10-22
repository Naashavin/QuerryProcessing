import pandas as pd

df = pd.read_xml("products.xml", parser="etree")
print("Products DataFrame:")
print(df)
