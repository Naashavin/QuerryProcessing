import pandas as pd

df = pd.read_csv("student_marks_binning.csv")

bins = [0, 40, 50, 60, 75, 100]
labels = ["Fail", "Pass", "Second Class", "First Class", "Distinction"]

df["Category"] = pd.cut(df["Marks"], bins=bins, labels=labels, right=False)

print("Categorized marks:")
print(df[["Name", "Marks", "Category"]])

print("\nNumber of students in each category:")
print(df["Category"].value_counts())
