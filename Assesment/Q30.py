import json
import pandas as pd

with open("employees_nested.json") as f:
    data = json.load(f)

rows = []
for emp in data:
    rows.append({
        "name": emp["name"],
        "city": emp["address"]["city"],
        "state": emp["address"]["state"]
    })

df = pd.DataFrame(rows)
print("Extracted Employee DataFrame:")
print(df)
