import sqlite3

DB_NAME = "data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            branch_name TEXT,
            claim_type TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_data(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pdf_data (customer_name, branch_name, claim_type)
        VALUES (?, ?, ?)
    ''', (data["customer_name"], data["branch_name"], data["account_number"]))
    conn.commit()
    conn.close()
