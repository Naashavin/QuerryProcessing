import pandas as pd

df = pd.read_csv("students_marks_outliers.csv")

mean = df["Marks"].mean()
std = df["Marks"].std()

print("Mean:", mean)
print("Standard Deviation:", std)

df["Z_score"] = (df["Marks"] - mean) / std

outliers = df[df["Z_score"].abs() > 2]
print("\nOutliers:")
print(outliers)

cleaned_df = df[df["Z_score"].abs() <= 2].drop(columns=["Z_score"])
print("\nCleaned dataset:")
print(cleaned_df)
