employees = {
    "Aarav": 70000,
    "Bhavna": 48000,
    "Chirag": 85000,
    "Divya": 52000,
    "Eeshan": 60000
}

highest_emp = max(employees, key=employees.get)
lowest_emp = min(employees, key=employees.get)
avg_salary = sum(employees.values()) / len(employees)

print("Highest salary employee:", highest_emp, "with salary:", employees[highest_emp])
print("Lowest salary employee:", lowest_emp, "with salary:", employees[lowest_emp])
print("Average salary:", avg_salary)
