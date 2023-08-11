"""Some database logic is defined here."""

import sqlite3


def open_database(sqlite_path: str) -> sqlite3.Connection:
    """Open SQLite database with given path and check its ability to perform queries on the required tables
    `social_groups` and `population_divided`.
    """
    database = sqlite3.connect(sqlite_path)

    cur = database.cursor()

    try:
        cur.execute("SELECT id, name, is_primary FROM social_groups LIMIT 1")
        cur.fetchone()
        cur.execute("SELECT house_id, age, social_group_id, men, women FROM population_divided LIMIT 1")
        cur.fetchone()
    finally:
        cur.close()

    return database
