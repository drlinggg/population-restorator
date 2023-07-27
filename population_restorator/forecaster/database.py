"""Some database logic is defined here."""

import sqlite3


def open_database(sqlite_path: str) -> sqlite3.Connection:
    """Open SQLite database with given path and check its ability to perform queries on the required tables
    `social_groups` and `population_divided`.
    """
    database = sqlite3.connect(sqlite_path)

    cur = database.cursor()

    try:
        cur.execute("SELECT id, name, is_primary FROM social_groups")
        cur.fetchone()
        cur.execute("SELECT house_id, is_male, age, social_group_id, people FROM population_divided")
        cur.fetchone()
    finally:
        cur.close()

    return database
