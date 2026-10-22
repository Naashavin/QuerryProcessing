import pandas as pd
import os

cust_file = "customers_table.csv" if os.path.exists("customers_table.csv") else "rel_customers.csv"
order_file = "orders.csv" if os.path.exists("orders.csv") else "rel_orders.csv"

customers = pd.read_csv(cust_file)
orders = pd.read_csv(order_file)

merged = pd.merge(customers, orders, on="CustomerID")
print("Joined tables:")
print(merged)

order_counts = merged.groupby("Name")["OrderID"].count()
more_than_three = order_counts[order_counts > 3]
print("\nCustomers with more than 3 orders:")
print(more_than_three)

total_spent = merged.groupby("Name")["Amount"].sum()
print("\nTotal purchase amount for each customer:")
print(total_spent)
