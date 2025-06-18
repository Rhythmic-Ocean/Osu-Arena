import sqlite3

def get_table_data():
    conn = sqlite3.connect("instance/rt4d.db")  # change path to your DB
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Silver")  # change table name
    rows = cursor.fetchall()
    headers = [description[0] for description in cursor.description]
    conn.close()
    return headers, rows

def main():
    headers, rows = get_table_data()

    if not rows:
        print("This table is empty")
        exit()
    else:
        formatted = " | ".join(headers) + "\n"
        formatted += "-" * 80 + "\n"
        for row in rows:
            formatted += " | ".join(str(item) for item in row) + "\n"
        print(formatted)

main()