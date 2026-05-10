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
    return cursor.execute("SELECT * FROM Payers ORDER BY payer_id").fetchall()

def add_payer(name):
    return cursor.execute("INSERT INTO Payers(name) VALUES (?) RETURNING payer_id", (name,)).fetchone()[0]

def update_payer(id, name):
    cursor.execute("UPDATE Payers SET name = ? WHERE payer_id = ?", (name, id))

def delete_payer(id):
    cursor.execute("DELETE FROM Payers WHERE payer_id = ?", (id,))

def get_splits():
    return cursor.execute("SELECT * FROM Payer_Splits ORDER BY split_id").fetchall()

def get_split_by_id(id):
    return cursor.execute("SELECT * FROM Payer_Splits WHERE split_id = ?", (id,)).fetchall()

def add_split(payer_splits):
    split_id = cursor.execute("INSERT INTO Splits DEFAULT VALUES RETURNING split_id").fetchone()[0]

    for payer_id, percent in payer_splits.items():
        cursor.execute("INSERT INTO Payer_Splits(split_id, payer_id, percent) VALUES (?, ?, ?)", (split_id, payer_id, percent))

    return split_id

def update_split(id, payer_splits):
    cursor.execute("DELETE FROM Payer_Splits WHERE split_id = ?", (id,))

    for payer_id, percent in payer_splits.items():
        cursor.execute("INSERT INTO Payer_Splits(split_id, payer_id, percent) VALUES (?, ?, ?)", (id, payer_id, percent))

def delete_split(id):
    cursor.execute("DELETE FROM Splits WHERE split_id = ?", (id,))

# Likely should be renamed to get_splits() in future refactor
def get_split_names():
    return cursor.execute("SELECT * FROM Splits ORDER BY split_id").fetchall()

def get_split_name_by_id(id):
    return cursor.execute("SELECT name FROM Splits WHERE split_id = ?", (id,)).fetchone()[0]

def update_split_name(id, name):
    cursor.execute("UPDATE Splits SET name = ? WHERE split_id = ?", (name, id))

def reset_data():
    cursor.execute("DROP TABLE Payer_Splits") # Drop first since it depends on Payers and Splits
    cursor.execute("DROP TABLE Payers")
    cursor.execute("DROP TABLE Splits")
    cursor.execute(create_payers_table)
    cursor.execute(create_split_table)
    cursor.execute(create_payer_split_table)