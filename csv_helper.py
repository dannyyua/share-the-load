import os
import shutil
import csv
import re
from globals import temp_file

# Copy the given CSV to a temp CSV file for assigning splits to
def transform_csv(filename):
    # Trim quotations
    filename = filename.strip('"')

    if not filename.endswith('.csv'):
        raise ValueError("File must be a CSV file")
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} does not exist")
    
    shutil.copy(filename, temp_file)

    rows = []
    
    with open(temp_file, 'r', newline='') as file:
        reader = csv.reader(file)

        # TODO: Yield
        # TODO: Check if file is not empty
        for row in reader:
            rows.append(row)

    rows[0].append("Split IDs")
    for row in rows[1:]:
        row.append('EDIT_ME')
    
    with open(temp_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(rows)

# Calculate the amounts owed by each payer based on the splits assigned to each row
def calculate_amounts(ps_dict):
    with open(temp_file, 'r', newline='') as file:
        reader = csv.reader(file)

        rows = []

        for row in reader:
            rows.append(row)

        # TODO: Find a better way to identify the amount column
        amount_indx = -1
        for i in range(len(rows[1])):
            if re.match(r'\d+\.\d+', rows[1][i]):
                amount_indx = i
                break

        if amount_indx == -1:
            raise ValueError("Could not find amount column in CSV file")

        totals_dict = {}

        for i in range(1, len(rows)):
            amount = float(rows[i][amount_indx])
            split_id = rows[i][-1]

            if split_id not in ps_dict and split_id != '0':
                print(f"Warning: Unknown Split ID '{split_id}' found in row {i+1}. Ignoring row. Please update the Split ID if this row should be included.")
                continue

            if split_id == '0':
                continue

            for (name, percent) in ps_dict[split_id]:
                if name not in totals_dict:
                    totals_dict[name] = 0

                totals_dict[name] += amount * (percent / 100)
            
        return totals_dict
