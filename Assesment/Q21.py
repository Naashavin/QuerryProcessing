import pandas as pd

df = pd.read_csv("attendance.csv")

below_75 = df[df["Attendance (%)"] < 75]
print("Students with attendance below 75%:")
print(below_75)

avg_attendance = df["Attendance (%)"].mean()
print("\nAverage attendance:", avg_attendance)

top_5 = df.sort_values(by="Attendance (%)", ascending=False).head(5)
print("\nTop 5 students with highest attendance:")
print(top_5)
