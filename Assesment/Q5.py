import pandas as pd
import os

file_name = "hospital.csv" if os.path.exists("hospital.csv") else "hospital_patients.csv"
df = pd.read_csv(file_name)

above_60 = df[df["Age"] > 60]
print("Patients whose age is above 60:")
print(above_60)

females = df[df["Gender"] == "Female"]
print("\nFemale patients:")
print(females)

diabetic_count = (df["Diabetic"] == "Yes").sum()
print("\nCount of diabetic patients:", diabetic_count)
