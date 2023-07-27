"""Additional social_groups balancing methods are defined here."""
import sqlite3
from math import ceil, floor

import numpy as np


def balance_year_additional_social_groups(cur: sqlite3.Cursor, rng: np.random.Generator) -> None:
    """Find houses with the number of social groups highly different from the statistical
    distribution and balance them.
    """
    cur.execute(
        "SELECT"
        "   pd.house_id,"
        "   pd.age,"
        "   pd.is_male,"
        "   pd.social_group_id,"
        "   pd.people,"
        "   population.people * sg.probability * ("
        "       CASE WHEN pd.is_male = true"
        "           THEN sgd.men_probability"
        "           ELSE sgd.women_probability"
        "       END"
        "    ) AS probable_people"
        " FROM population_divided pd JOIN ("
        "        SELECT house_id, sum(people) AS people"
        "        FROM population_divided pd JOIN social_groups sg ON pd.social_group_id = sg.id"
        "        WHERE sg.is_primary = true"
        "        GROUP by house_id"
        "   ) population ON pd.house_id = population.house_id"
        "   JOIN social_groups sg ON pd.social_group_id = sg.id"
        "   JOIN social_groups_distribution sgd ON sgd.social_group_id = sg.id AND pd.age = sgd.age"
        " WHERE sg.is_primary = false AND ("
        "   pd.people > probable_people * 2"
        "   OR pd.people + 2 < probable_people / 2"
        ")"
        " ORDER BY 1, 2, 3, 4, 5"
    )

    for house_id, age, is_male, sg_id, people, probable_people in cur.fetchall():
        if people > probable_people * 2:
            needed = probable_people * 2
        else:
            needed = probable_people / 2
        needed = ceil(probable_people * 2) if rng.integers(0, 1, 1, endpoint=True)[0] else floor(probable_people)

        cur.execute(
            "UPDATE population_divided"
            " SET people = ?"
            " WHERE house_id = ? AND age = ? AND social_group_id = ? AND is_male = ?",
            (needed, house_id, age, sg_id, is_male),
        )
