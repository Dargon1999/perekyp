import sqlite3
import os

db_path = os.path.join("instance", "site.db")

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Checking 'client' table schema...")
    cursor.execute("PRAGMA table_info(client)")
    columns = [info[1] for info in cursor.fetchall()]
    print(f"Columns: {columns}")

    if "username" not in columns:
        print("Adding 'username' column...")
        cursor.execute("ALTER TABLE client ADD COLUMN username VARCHAR(100)")
        conn.commit()
        print("Column 'username' added successfully.")
    else:
        print("Column 'username' already exists.")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    conn.close()
