"""People division methods are defined here."""
from __future__ import annotations

import itertools
import sqlite3

import pandas as pd
from loguru import logger
from tqdm import tqdm

from population_restorator.models.social_groups import SocialGroupsDistribution


def save_houses_distribution_to_sqlite(  # pylint: disable=too-many-locals,too-many-branches
    sqlite_db_or_path: str | sqlite3.Connection,
    distribution: pd.Series,
    houses_capacity: pd.Series,
    distribution_probabilities: SocialGroupsDistribution,
    verbose: bool = False,
) -> None:
    """Save the given people division to the SQLite database

    Args:
        sqlite_path (str): path to create/open SQLite database
        distribution (pd.Series): Series with integer identifiers as an index and numpy.ndarrays as values
        func (Callable[[np.ndarray], dict[str, PeopleDistribution]]): _description_
    """
    func = distribution_probabilities.get_resulting_function()
    if isinstance(sqlite_db_or_path, str):
        database = sqlite3.connect(sqlite_db_or_path)
    else:
        database = sqlite_db_or_path

    if distribution.shape[0] == 0:
        logger.warning("Requested to save an empty people division. Exiting without writing database.")
        return

    try:
        cur: sqlite3.Cursor = database.cursor()

        cur.execute(
            "CREATE TABLE IF NOT EXISTS social_groups ("
            "   id INTEGER PRIMARY KEY,"
            "   name varchar(150) UNIQUE NOT NULL,"
            "   probability REAL NOT NULL,"
            "   is_primary boolean NOT NULL"
            ")"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS houses ("
            "   id INTEGER PRIMARY KEY NOT NULL,"
            "   capacity float NOT NULL"  # living_area, max_population, etc.
            ")"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS social_groups_distribution ("
            "   social_group_id INTEGER REFERENCES social_groups(id) NOT NULL,"
            "   age INTEGER NOT NULL,"
            "   men_probability REAL NOT NULL,"
            "   women_probability REAL NOT NULL"
            ")"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS population_divided ("
            "   house_id INTEGER REFERENCES houses(id) NOT NULL,"
            "   age INTEGER NOT NULL,"
            "   social_group_id INTEGER REFERENCES social_groups(id) NOT NULL,"
            "   men INTEGER NOT NULL,"
            "   women INTEGER NOT NULL,"
            "   PRIMARY KEY (house_id, age, social_group_id)"
            ")"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS population_divided_house_age_social_group"
            " ON population_divided (house_id, age, social_group_id)"
        )

        for house_id, living_area in houses_capacity.items():
            cur.execute(
                "INSERT INTO houses (id, capacity) VALUES (?, ?) ON CONFLICT DO NOTHING", (house_id, living_area)
            )

        social_groups_ids = {}
        for is_primary, social_group in itertools.chain(
            zip(itertools.repeat(True), distribution_probabilities.primary),
            zip(itertools.repeat(False), distribution_probabilities.additional),
        ):
            cur.execute("SELECT id FROM social_groups WHERE name = ?", (social_group.name,))
            idx = cur.fetchone()
            if idx is None:
                cur.execute(
                    "INSERT INTO social_groups (name, probability, is_primary) VALUES (?, ?, ?) RETURNING id",
                    (social_group.name, float(social_group.probability), is_primary),
                )
                idx = cur.fetchone()
                for age, men, women in zip(
                    itertools.count(), social_group.distribution.men, social_group.distribution.women
                ):
                    cur.execute(
                        "INSERT INTO social_groups_distribution"
                        " (social_group_id, age, men_probability, women_probability) VALUES (?, ?, ?, ?)",
                        (idx[0], age, float(men), float(women)),
                    )
            social_groups_ids[social_group.name] = idx[0]

        iterable = (
            tqdm(distribution.items(), total=len(distribution), desc="Saving houses")
            if verbose
            else iter(distribution.items())
        )
        for house_id, distribution_array in iterable:
            for social_group_name, people_division in func(distribution_array).items():
                social_group_id = social_groups_ids.get(social_group_name)
                if social_group_id is None:
                    raise ValueError(
                        f"Could not insert people division because social group '{social_group_name}' is not present"
                    )
                for age, (men, women) in enumerate(zip(people_division.men, people_division.women)):
                    # insert_data(house_id, True, age, social_group_id, people)
                    cur.execute(
                        "INSERT INTO population_divided (house_id, age, social_group_id, men, women)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (house_id, age, social_group_id, men, women),
                    )

        database.commit()
    finally:
        if isinstance(sqlite_db_or_path, str):
            database.close()
