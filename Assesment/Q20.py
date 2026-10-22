import pandas as pd

df = pd.read_csv("customers.csv")

highest_spender = df.loc[df["PurchaseAmount"].idxmax()]
print("Customer with highest purchase amount:")
print(highest_spender)

avg_amount = df["PurchaseAmount"].mean()
print("\nAverage purchase amount:", avg_amount)

high_spenders = df[df["PurchaseAmount"] > avg_amount]
print("\nCustomers with purchase amount greater than average:")
print(high_spenders)

high_spenders.to_csv("high_spenders.csv", index=False)
