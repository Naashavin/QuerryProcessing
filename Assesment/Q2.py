import pandas as pd

df = pd.read_csv("student_marks.csv")

print("Missing values in dataset:")
print(df.isnull().sum())

df = df.fillna(df.mean(numeric_only=True))

print("\nCleaned dataset:")
print(df)
