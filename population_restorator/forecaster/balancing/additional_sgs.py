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
        "   pd.social_group_id,"
        "   pd.men,"
        "   pd.women,"
        "   population.men * sg.probability * sgd.men_probability AS probable_men,"
        "   population.women * sg.probability * sgd.women_probability AS probable_women"
        " FROM population_divided pd JOIN ("
        "        SELECT house_id, sum(men) AS men, sum(women) AS women AS people"
        "        FROM population_divided pd JOIN social_groups sg ON pd.social_group_id = sg.id"
        "        WHERE sg.is_primary = true"
        "        GROUP by house_id"
        "   ) population ON pd.house_id = population.house_id"
        "   JOIN social_groups sg ON pd.social_group_id = sg.id"
        "   JOIN social_groups_distribution sgd ON sgd.social_group_id = sg.id AND pd.age = sgd.age"
        " WHERE sg.is_primary = false AND ("
        "   pd.men > probable_men * 2"
        "   OR pd.men + 2 < probable_men / 2"
        "   OR pd.women > probable_women * 2"
        "   OR pd.women + 2 < probable_women / 2"
        ")"
        " ORDER BY 1, 2, 3"
    )

    for house_id, age, sg_id, men, women, probable_men, probable_women in cur.fetchall():
        if men > probable_men * 2:
            needed_men = probable_men * 1.5
        elif men < probable_men / 2:
            needed_men = probable_men / 1.5
        needed_men = ceil(needed_men) if rng.integers(0, 1, 1, endpoint=True)[0] else floor(probable_men)

        if women > probable_women * 2:
            needed_women = probable_women * 1.5
        elif women < probable_women / 2:
            needed_women = probable_women / 1.5
        needed_women = ceil(needed_women) if rng.integers(0, 1, 1, endpoint=True)[0] else floor(probable_women)

        cur.execute(
            "UPDATE population_divided"
            " SET men = ?, women = ?"
            " WHERE house_id = ? AND age = ? AND social_group_id = ?",
            (needed_men, needed_women, house_id, age, sg_id),
        )
