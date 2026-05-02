import os
import shutil
import csv
import re
from globals import temp_file

def get_csv_rows():
    # TODO: Yield
    # TODO: Check if file is not empty
    with open(temp_file, 'r', newline='') as file:
        reader = csv.reader(file)

        rows = []

        for row in reader:
            rows.append(row)

        return rows

# Copy the given CSV to a temp CSV file for assigning splits to
def transform_csv(filename):
    # Trim quotations
    filename = filename.strip('"')

    if not filename.endswith('.csv'):
        raise ValueError("File must be a CSV file")
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} does not exist")
    
    shutil.copy(filename, temp_file)

    rows = get_csv_rows()

    rows[0].append("Split IDs")
    for row in rows[1:]:
        row.append('0')
    
    with open(temp_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(rows)

# Calculate the amounts owed by each payer based on the splits assigned to each row
def calculate_amounts(ps_dict):
    rows = get_csv_rows()

    totals_dict = {}

    for i in range(1, len(rows)):
        split_id = rows[i][-1]

        # Ignore if split ID is 0
        if split_id == '0':
            continue

        # Try to find a currency amount in the row
        matches = [bool(re.match(r'^-?\d+\.?\d*$', val)) for val in rows[i][:-1]]
        if True not in matches:
            print(f"Warning: No transaction amount found in row {i+1}. Ignoring row.")
            continue

        amount_indx = matches.index(True)
        amount = float(rows[i][amount_indx])

        if split_id not in ps_dict:
            print(f"Warning: Unknown Split ID '{split_id}' found in row {i+1}. Ignoring row. Please update the Split ID if this row should be included.")
            continue

        for (name, percent) in ps_dict[split_id]:
            if name not in totals_dict:
                totals_dict[name] = 0

            totals_dict[name] += amount * (percent / 100)
        
    return totals_dict
