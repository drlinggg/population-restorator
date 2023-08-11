"""Primary social groups balancing methods are defined here."""
import sqlite3
from math import ceil, floor

import numpy as np
from loguru import logger


def _fix_people_number(  # pylint: disable=too-many-locals,too-many-arguments
    cur: sqlite3.Cursor,
    house_id: int,
    age: int,
    sg_id: int,
    current: int,
    probable: int,
    is_male: bool,
    rng: np.random.Generator,
) -> None:
    """Return estimated number of people required."""
    if current > probable * 2:
        needed = probable * 1.5
    elif current < probable / 2:
        needed = probable / 1.5
    else:
        return
    needed = ceil(needed) if rng.integers(0, 1, 1, endpoint=True)[0] else floor(probable)

    cur.execute(
        "SELECT sg.id, sgd.men_probability, sgd.women_probability"
        " FROM social_groups sg JOIN social_groups_distribution sgd ON sgd.social_group_id = sg.id"
        " WHERE sg.is_primary = true"
        "   AND age = ?"
        "   AND sgd.men_probability > 0 or sgd.women_probability > 0"
        "   AND sg.id <> ?",
        (age, sg_id),
    )
    sgs_ids: list[int] = []
    sgs_probs: list[int] = []
    for other_sg_id, men_prob in cur:
        if men_prob > 0:
            sgs_ids.append(other_sg_id)
            sgs_probs.append(men_prob)

    if len(sgs_ids) == 0:
        if probable == 0:
            logger.warning(
                "Could not resettle {} {} of the age {} from house_id = {} which have social_group_id = {}"
                " and should have been discarded",
                current,
                ("men" if is_male else "women"),
                age,
                house_id,
                sg_id,
            )
        return

    if len(sgs_probs) > 1:
        sgs_probs = np.array(sgs_probs) / sum(sgs_probs)

    change_values = (
        np.unique(
            rng.choice(list(range(len(sgs_ids))), abs(current - needed), replace=True, p=sgs_probs),
            return_counts=True,
        )
        if len(sgs_ids) != 1
        else ([sgs_ids[0]], [abs(current - needed)])
    )

    for idx, change in zip(change_values[0], change_values[1]):
        needed_sg_id = sgs_ids[idx]
        cur.execute(
            "UPDATE population_divided SET {sex} = {sex} + ?"
            " WHERE house_id = ? AND social_group_id = ? AND age = ?".format(sex=("men" if is_male else "women")),
            (int(change), house_id, needed_sg_id, age),
        )
        if cur.rowcount == 0:
            cur.execute(
                "INSERT INTO population_divided (house_id, age, social_group_id, men, women) VALUES (?, ?, ?, ?, ?)",
                (house_id, age, needed_sg_id, (int(change) if is_male else 0), (0 if is_male else int(change))),
            )
        cur.execute(
            "UPDATE population_divided"
            f" SET {'man' if is_male else 'women'} = ?"
            " WHERE house_id = ? AND age = ? AND social_group_id = ?",
            (needed, house_id, age, sg_id),
        )


def balance_year_primary_social_groups(cur: sqlite3.Cursor, rng: np.random.Generator) -> None:
    """Increase or decrease number of people with concrete primary social groups while preserving total
    number of people with set sex and age constant.
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
        _fix_people_number(cur, house_id, age, sg_id, men, probable_men, True, rng)
        _fix_people_number(cur, house_id, age, sg_id, women, probable_women, False, rng)
