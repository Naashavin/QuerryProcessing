import xml.etree.ElementTree as ET

tree = ET.parse("employee.xml")
root = tree.getroot()

employees = root.findall("employee")

print("Employee names:")
for emp in employees:
    print(emp.find("name").text)

print("\nTotal employees:", len(employees))
