import pandas as pd
import os

file_name = "students.xml" if os.path.exists("students.xml") else "students_records.xml"
df = pd.read_xml(file_name, parser="etree")

print("All student names:")
print(df["name"].tolist())

print("\nStudent count in each department:")
print(df["department"].value_counts())

toppers = df.loc[df.groupby("department")["marks"].idxmax()]
print("\nTopper from each department:")
print(toppers[["department", "name", "marks"]])
