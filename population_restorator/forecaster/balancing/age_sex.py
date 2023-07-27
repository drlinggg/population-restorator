"""Age-sex balancing methods are defined here."""
import sqlite3

import numpy as np
from loguru import logger


def _increase_population(
    cur: sqlite3.Cursor, age: int, increase_needed: int, is_male: bool, rng: np.random.Generator
) -> None:
    """Add people of the given age and sex to the houses."""
    cur.execute(
        "SELECT h.id, sum(p.people) / h.capacity as load FROM population_divided p"
        "   JOIN houses h ON p.house_id = h.id"
        "   JOIN social_groups sg ON p.social_group_id = sg.id"
        " WHERE sg.is_primary = true AND p.is_male = ?"
        " GROUP by h.id, h.capacity"
        " HAVING load > 0",
        (is_male,),
    )
    # pylint: disable=unnecessary-direct-lambda-call
    houses_ids, houses_probs = (lambda loads: (list(loads.keys()), np.array(list(loads.values()))))(dict(cur))

    cur.execute(
        f"SELECT sg.id, sg.probability * sgd.{'men' if is_male else 'women'}_probability"
        " FROM social_groups sg"
        "   JOIN social_groups_distribution sgd ON sg.id = sgd.social_group_id AND sgd.age = ?"
        f" WHERE sg.is_primary = true AND sg.probability * sgd.{'men' if is_male else 'women'}_probability > 0",
        (age,),
    )
    # pylint: disable=unnecessary-direct-lambda-call
    sgs_ids, sgs_probs = (lambda probs: (list(probs.keys()), np.array(list(probs.values()))))(dict(cur))

    total_probs = np.array((np.mat(houses_probs).T * sgs_probs).flat)
    total_probs /= total_probs.sum()

    change_values = np.unique(
        rng.choice(list(range(len(houses_ids) * len(sgs_ids))), increase_needed, replace=True, p=total_probs),
        return_counts=True,
    )
    for idx, change in zip(change_values[0], change_values[1]):
        house_id = houses_ids[idx // len(sgs_ids)]
        sg_id = sgs_ids[idx % len(sgs_ids)]
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


def _decrease_population(
    cur: sqlite3.Cursor, age: int, decrease_needed: int, is_male: bool, rng: np.random.Generator
) -> None:
    """Remove people of the given age and sex from houses."""
    cur.execute(
        "SELECT house_id, sg.id, sum(p.people * (1 - sg.probability)) as load FROM population_divided p"
        "   JOIN social_groups sg ON p.social_group_id = sg.id"
        " WHERE p.is_male = ? and sg.is_primary = true"
        " GROUP BY house_id, sg.id"
        " ORDER BY house_id",
        (is_male,),
    )
    houses_sgs_ids = []
    houses_sgs_probs = []
    for house_id, sg_id, load in cur:
        houses_sgs_ids.append((house_id, sg_id))
        houses_sgs_probs.append(load)

    houses_sgs_probs = np.array(houses_sgs_probs)
    houses_sgs_probs /= houses_sgs_probs.sum()

    change_values = np.unique(
        rng.choice(list(range(len(houses_sgs_ids))), decrease_needed, replace=True, p=houses_sgs_probs),
        return_counts=True,
    )
    for h_s_id, change in zip(change_values[0], change_values[1]):
        house_id, sg_id = houses_sgs_ids[h_s_id]
        cur.execute(
            "UPDATE population_divided SET people = people - ?"
            " WHERE house_id = ? AND social_group_id = ? AND age = ? and is_male = ?",
            (int(change), house_id, sg_id, age, is_male),
        )


def balance_year_age_sex(
    cur: sqlite3.Cursor, age: int, poeople_needed: int, is_male: bool, rng: np.random.Generator
) -> None:
    """Increase or decrease population of houses to get needed summary number of people of the given age and sex."""
    MAX_TRIES = 5  # pylint: disable=invalid-name
    for _ in range(MAX_TRIES):
        cur.execute(
            "SELECT sum(people) FROM population_divided p"
            "   JOIN social_groups sg ON p.social_group_id = sg.id"
            " WHERE p.age = ? AND p.is_male = ? AND sg.is_primary = true",
            (age, is_male),
        )
        people_in_db: int = cur.fetchone()[0] or 0
        if people_in_db == poeople_needed:
            return

        logger.trace("{} of age {}: {} -> {}", ("men" if is_male else "women"), age, people_in_db, poeople_needed)
        if people_in_db < poeople_needed:
            _increase_population(cur, age, poeople_needed - people_in_db, is_male, rng)
        else:
            _decrease_population(cur, age, people_in_db - poeople_needed, is_male, rng)

    logger.warning(
        "Could not update {} number of age {}: {} -> {} by {} tries",
        ("men" if is_male else "women"),
        age,
        people_in_db,
        poeople_needed,
        MAX_TRIES,
    )
