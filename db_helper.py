import sqlite3
from db_scripts import *

def start_db():
    global cursor

    # Connect to DB
    conn = sqlite3.connect("data.db", autocommit=True)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = 1") # Enforce foreign key constraints

    cursor.execute(create_payers_table)
    cursor.execute(create_split_table)
    cursor.execute(create_payer_split_table)

    return cursor

def get_payers():
    return cursor.execute("SELECT * FROM Payers").fetchall()

def add_payer(name):
    cursor.execute("INSERT INTO Payers(name) VALUES (?)", (name,))

def update_payer(id, name):
    cursor.execute("UPDATE Payers SET name = ? WHERE payer_id = ?", (name, id))

def delete_payer(id):
    cursor.execute("DELETE FROM Payers WHERE payer_id = ?", (id,))