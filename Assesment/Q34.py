import xml.etree.ElementTree as ET
import os

file_name = "products.xml" if os.path.exists("products.xml") else "products_prices.xml"
tree = ET.parse(file_name)
root = tree.getroot()

for product in root.findall("product"):
    price = product.find("price")
    new_price = float(price.text) * 1.10
    price.text = str(round(new_price, 2))
    print(product.find("name").text, "updated price:", price.text)

tree.write("products_updated.xml")
print("\nUpdated XML saved to products_updated.xml")
