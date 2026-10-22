import pandas as pd

df = pd.read_csv("student.csv")

json_data = df.to_json(orient="records", indent=4)
print("JSON format:")
print(json_data)

with open("student.json", "w") as f:
    f.write(json_data)
