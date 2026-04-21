import sqlite3
import sys
import msvcrt
import subprocess
import random
import time
import os
from collections import defaultdict
from csv_helper import transform_csv, calculate_amounts
from db_scripts import *
from globals import temp_file

# Connect to DB
conn = sqlite3.connect("data.db", autocommit=True)
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = 1") # Enforce foreign key constraints

# Same as print() but clears the console first
def cprint(*args, **kwargs):
    subprocess.run(["cls"], shell=True)
    print(*args, **kwargs)

# Convenience function
def clear_console():
    cprint("")

# Wait for user to press a key
def prompt_keypress(clear_console=True):
    print("\nPress any key to continue...")
    msvcrt.getch()
    if clear_console:
        clear_console()

# Returns a dict where each entry contains all payers info for a given split
def get_split_dict():
    splits = cursor.execute("SELECT S.split_id, P.name, PS.percent FROM Payers P JOIN Payer_Splits PS ON P.payer_id = PS.payer_id JOIN Splits S ON PS.split_id = S.split_id").fetchall()
    split_dict = defaultdict(list)

    for s in splits:
        split_dict[str(s[0])].append((s[1], s[2]))

    return split_dict

# Copy given CSV, prompt user to assign splits, then calculate amounts owed and output results
def process_csv():
    clear_console()

    payer_splits_count = cursor.execute("SELECT COUNT(*) FROM Payer_Splits").fetchone()[0]
    if payer_splits_count == 0:
        print("Please create at least one Payer and one Split before processing a CSV file.")
        prompt_keypress()
        return

    splits = get_split_dict()

    if os.path.isfile(temp_file):
        prompt = "Please enter the path of the payments CSV file (or 'e' to edit the existing file, or 'r' to view results): "
    else:
        prompt = "Please enter the path of the payments CSV file: "

    user_input = input(prompt)

    if not os.path.isfile(temp_file):
        transform_csv(user_input)

    if user_input != 'r':
        print("\nAvailable Splits:")
        for id, payers in splits.items():
            print(f"{id}: {', '.join([f'{p[0]} ({p[1]}%)' for p in payers])}")
        print()

        print("The payments CSV file will open, please update the newly added 'Split IDs' column values using the IDs listed above (or leave as 0 to ignore a row). Save and close when done.")
        prompt_keypress(False)
        print("Opening CSV file for editing...")
        subprocess.run([temp_file], shell=True)

    # Just for fun :)
    cprint("Processing", end="", flush=True)
    for _ in range(random.randrange(3, 6)):
        print(".", end="", flush=True)
        time.sleep(0.2)
    print()

    totals = calculate_amounts(splits)

    print("\nTotals:")

    for name, amount in totals.items():
        print(f"{name} pays: ${amount:.2f}")
    if not totals:
        print("No amounts calculated. Please ensure the 'Split IDs' column has been updated, otherwise calculations will not work.")
    prompt_keypress()

# Create a payer with a given name
def add_payer():
    clear_console()

    while True:
        name = input("Enter the name of the new Payer (or leave empty to finish): ")
        if not name:
            break
        cursor.execute("INSERT INTO Payers(name) VALUES (?)", (name,)) # Comma to make it a tuple
        print(f"Added new Payer {name}.")

    clear_console()

# Create a split where each payer is assigned a percentage of what they owe
def add_split():
    clear_console()

    payer_splits = {}

    payers = cursor.execute("SELECT payer_id, name FROM Payers").fetchall()
    payers_dict = {str(p[0]): p[1] for p in payers}
    print("Available Payers:")
    for p in payers:
        print(f"{p[0]}: {p[1]}")
    if not payers:
        print("No Payers found. Please add a Payer before creating a Split.\n")
        prompt_keypress()
        return

    while True:
        payer_id = input("Enter the Payer ID (or leave empty to finish): ")
        if not payer_id:
            break
        if payer_id not in payers_dict:
            print(f"Payer ID not found. Valid payer IDs: {', '.join(payers_dict.keys())}")
            continue
        percent = input(rf"Enter as a percent (%) what {payers_dict[payer_id]} will owe (0% - 100%): ")
        percent = percent.replace("%", "")

        try:
            percent_val = float(percent)
            if percent_val < 0 or percent_val > 100:
                print("Percent must be between 0 and 100.")
                continue
        except ValueError:
            print("Invalid percent value.")
            continue

        payer_splits[payer_id] = percent
        print(f"{payers_dict[payer_id]} will owe {percent}% in the current Split.")

    if payer_splits:
        split_id = cursor.execute("INSERT INTO Splits DEFAULT VALUES RETURNING split_id").fetchone()[0]
        for payer_id, percent in payer_splits.items():
            cursor.execute("INSERT INTO Payer_Splits(payer_id, split_id, percent) VALUES (?, ?, ?)", (payer_id, split_id, percent))

    clear_console()

# Reset all DB tables
def reset_data():
    clear_console()

    option = input("Are you sure you want to reset all data? This cannot be undone. (y/n): ")
    if option.lower() != 'y':
        print("Reset cancelled.\n")
        return
    
    cursor.execute("DROP TABLE Payer_Splits") # Drop first since it depends on Payers and Splits
    cursor.execute("DROP TABLE Payers")
    cursor.execute("DROP TABLE Splits")
    cursor.execute(create_payers_table)
    cursor.execute(create_split_table)
    cursor.execute(create_payer_split_table)
    if os.path.isfile(temp_file):
        os.remove(temp_file)

    print("Reset completed.\n")

# A bit of help for new users
def show_help():
    clear_console()

    print("To get started, first create at least one Payer and one Split. A Payer is simply anybody who you will be sharing payments with.")
    print("A Split determines who shares the load for a given transaction, and what each person's share is.")
    print("For example, you might share a few meals with Alice, and then split groceries three-ways between Alice and Bob. In this case, you would create two Splits - ")
    print(" one for the meal where Alice pays 50%, and one for the groceries where Alice and Bob each pay around 33%.")
    print("These Splits can then be reused in future transactions, simply by filling in the payment CSV with each Split's respective ID.")
    print("The software will automatically calculate how much each person's share is and give you a summary at the end.")
    print("It's that simple :)")

    prompt_keypress()

def exit():
    print("Goodbye!")
    sys.exit()

# Main input loop to prompt the user
def main():
    cursor.execute(create_payers_table)
    cursor.execute(create_split_table)
    cursor.execute(create_payer_split_table)

    clear_console() # Clear the console

    payer_splits_count = cursor.execute("SELECT COUNT(*) FROM Payer_Splits").fetchone()[0]
    if payer_splits_count == 0:
        print("Welcome! If this is your first time using Share the Load, please start by adding at least one Payer and a Split.")

    while True:
        print("Welcome to Share the Load! Please input one of the following options:")
        print("1: Process a Payment CSV")
        print("2: Add a Payer")
        print("3: Add a Split")
        print("4: Reset Data")
        print("5: Help")
        print("6: Exit")

        option = input("\nEnter your choice (e.g. 2): ")

        if option == "1":
            process_csv()
        elif option == "2":
            add_payer()
        elif option == "3":
            add_split()
        elif option == "4":
            reset_data()
        elif option == "5":
            show_help()
        elif option == "6":
            exit()
        else:
            print("Option not recognised. Please try again.")


if __name__ == "__main__":
    main()