import json

with open("students.json") as f:
    data = json.load(f)

print("Student names:")
for s in data:
    print(s["name"])

topper = max(data, key=lambda s: s["marks"])
print("\nTopper is", topper["name"], "with marks", topper["marks"])
