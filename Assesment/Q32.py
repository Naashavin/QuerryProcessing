import json

with open("students.json") as f:
    data = json.load(f)

for s in data:
    if s["marks"] >= 90:
        s["Grade"] = "A"
    elif s["marks"] >= 75:
        s["Grade"] = "B"
    elif s["marks"] >= 60:
        s["Grade"] = "C"
    elif s["marks"] >= 50:
        s["Grade"] = "D"
    else:
        s["Grade"] = "F"

with open("students_updated.json", "w") as f:
    json.dump(data, f, indent=4)

print("Updated students data:")
print(json.dumps(data, indent=4))
