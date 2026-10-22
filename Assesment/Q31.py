import json

with open("weather.json") as f:
    data = json.load(f)

for item in data:
    print("City:", item["city"])
    print("Temperature:", item["temperature"])
    print("Humidity:", item["humidity"])
    print("Wind Speed:", item["wind_speed"])
    print()

hottest = max(data, key=lambda x: x["temperature"])
print("Hottest city:", hottest["city"], "with temperature:", hottest["temperature"])
