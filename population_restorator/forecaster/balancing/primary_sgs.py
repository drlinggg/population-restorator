"""Primary social groups balancing methods are defined here."""
import sqlite3
from math import ceil, floor

import numpy as np
from loguru import logger


def balance_year_primary_social_groups(cur: sqlite3.Cursor, rng: np.random.Generator) -> None:
    """Increase or decrease number of people with concrete primary social groups while preserving total
    number of people with set sex and age constant.
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
        "         SELECT house_id, sum(people) AS people"
        "         FROM population_divided pd JOIN social_groups sg ON pd.social_group_id = sg.id"
        "         WHERE sg.is_primary = true"
        "         GROUP by house_id"
        "   ) population ON pd.house_id = population.house_id"
        "   JOIN social_groups sg ON pd.social_group_id = sg.id"
        "   JOIN social_groups_distribution sgd ON sgd.social_group_id = sg.id AND pd.age = sgd.age"
        " WHERE sg.is_primary = true AND ("
        "   pd.people - 2 > probable_people * 2"  # this is part where query differs from additional sgs
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
            f"SELECT sg.id, sgd.{'men' if is_male else 'women'}_probability"
            " FROM social_groups sg JOIN social_groups_distribution sgd ON sgd.social_group_id = sg.id"
            " WHERE sg.is_primary = true"
            "   AND age = ?"
            f"   AND sgd.{'men' if is_male else 'women'}_probability > 0"
            "   AND sg.id <> ?",
            (age, sg_id),
        )
        # pylint: disable=unnecessary-direct-lambda-call
        sgs_ids, sgs_probs = (lambda probs: (list(probs.keys()), np.array(list(probs.values()))))(dict(cur))
        if len(sgs_ids) == 0:
            if probable_people == 0:
                logger.warning(
                    "Could not resettle {} {} of the age {} from house_id = {} which have social_group_id = {}"
                    " and should have been discarded",
                    people,
                    ("men" if is_male else "women"),
                    age,
                    house_id,
                    sg_id,
                )
            continue
        sgs_probs /= sgs_probs.sum()
        if len(sgs_ids) == 1:
            cur.execute(
                "UPDATE population_divided"
                " SET people = people + ?"
                " WHERE house_id = ? AND age = ? AND social_group_id = ? AND is_male = ?",
                (abs(people - needed), house_id, age, sgs_ids[0], is_male),
            )
            if cur.rowcount == 0:
                cur.execute(
                    "INSERT INTO population_divided (house_id, age, social_group_id, is_male, people)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (house_id, age, sgs_ids[0], is_male(abs(people - needed))),
                )
        else:
            change_values = np.unique(
                rng.choice(list(range(len(sgs_ids))), abs(people - needed), replace=True, p=sgs_probs),
                return_counts=True,
            )
            for idx, change in zip(change_values[0], change_values[1]):
                sg_id = sgs_ids[idx]
                cur.execute(
                    "UPDATE population_divided SET people = people + ?"
                    " WHERE house_id = ? AND social_group_id = ? AND age = ? and is_male = ?",
                    (int(change), house_id, sg_id, age, is_male),
                )
                if cur.rowcount == 0:
                    cur.execute(
                        "INSERT INTO population_divided (house_id, age, social_group_id, is_male, people)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (house_id, age, sg_id, is_male, int(change)),
                    )

        cur.execute(
            "UPDATE population_divided"
            " SET people = ?"
            " WHERE house_id = ? AND age = ? AND social_group_id = ? AND is_male = ?",
            (needed, house_id, age, sg_id, is_male),
        )
