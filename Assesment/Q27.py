import pandas as pd

df = pd.read_csv("orders_dates.csv")
df["OrderDate"] = pd.to_datetime(df["OrderDate"])

monthly_orders = df["OrderDate"].dt.month.value_counts()
print("Orders placed each month:")
print(monthly_orders)

weekend_orders = df[df["OrderDate"].dt.dayofweek.isin([5, 6])]
print("\nOrders placed on weekends:")
print(weekend_orders)
