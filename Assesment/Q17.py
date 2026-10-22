marks = [78, 85, 34, 90, 62, 45, 88, 29, 95, 53]

highest = max(marks)
lowest = min(marks)
average = sum(marks) / len(marks)
passed = [m for m in marks if m >= 40]

print("Marks:", marks)
print("Highest mark:", highest)
print("Lowest mark:", lowest)
print("Average mark:", average)
print("Number of students passed:", len(passed))
