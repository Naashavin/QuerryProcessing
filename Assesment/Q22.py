import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("daily_sales_trend.csv")
df["Date"] = pd.to_datetime(df["Date"])

daily_sales = df.groupby("Date")["Sales Amount"].sum()
print("Daily sales:")
print(daily_sales)

max_day = daily_sales.idxmax()
print("\nDay with maximum sales:", max_day, "with sales:", daily_sales.max())

monthly_sales = df.set_index("Date").resample("ME")["Sales Amount"].sum()
print("\nMonthly sales:")
print(monthly_sales)

monthly_sales.plot(kind="bar")
plt.title("Monthly Sales")
plt.xlabel("Month")
plt.ylabel("Sales Amount")
plt.tight_layout()
plt.savefig("monthly_sales_trend.png")
plt.close()
