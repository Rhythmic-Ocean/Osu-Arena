import datetime

# 1. Get the full date (Year-Month-Day)
today = datetime.date.today()
print(today)  # Output: 2025-12-20

# 2. Get just the day of the week (e.g., "Saturday")
day_name = today.strftime("%A")
print(day_name)  # Output: Saturday
if day_name == "Sunday":
    print("hehe")
elif day_name == "Saturday":
    print("nono")

# 3. Get the day number (1-31)
day_number = today.day
print(day_number)  # Output: 20
