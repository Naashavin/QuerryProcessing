import csv
import sys
from collections import defaultdict
from config import SEED_CSV_PATH

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open(SEED_CSV_PATH, mode="r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    columns = reader.fieldnames or []

missing = {col: 0 for col in columns}
distinct_vals = defaultdict(set)

for row in rows:
    for col in columns:
        val = (row.get(col) or "").strip()
        if val == "" or val.upper() == "NA":
            missing[col] += 1
        else:
            distinct_vals[col].add(val)

print(f"Total rows in seed CSV: {len(rows)}")
print("\nMissing values per column (including empty and 'NA'):")
for col in columns:
    print(f"  {col:<14}: {missing[col]}")

print("\nDistinct spellings in categorical columns:")
for col in ("gender", "department", "visit_date", "fee_paid"):
    vals = sorted(distinct_vals[col])
    print(f"  {col:<14} ({len(vals)}): {vals}")
