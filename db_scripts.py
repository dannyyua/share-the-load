create_payers_table = """
CREATE TABLE IF NOT EXISTS Payers (
    payer_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT COLLATE NOCASE UNIQUE
)
"""

create_split_table = """
CREATE TABLE IF NOT EXISTS Splits (
    split_id    INTEGER PRIMARY KEY AUTOINCREMENT
)
"""

create_payer_split_table = """
CREATE TABLE IF NOT EXISTS Payer_Splits (
    payer_id    INTEGER,
    split_id    INTEGER,
    percent     REAL CHECK(percent >= 0 AND percent <= 100),
    PRIMARY KEY (payer_id, split_id),
    FOREIGN KEY (payer_id) REFERENCES Payers(payer_id) ON DELETE CASCADE,
    FOREIGN KEY (split_id) REFERENCES Splits(split_id) ON DELETE CASCADE
)
"""