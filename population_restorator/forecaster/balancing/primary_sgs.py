"""Primary social groups balancing methods are defined here."""
from __future__ import annotations

from math import ceil, floor
from typing import Callable

import numpy as np
from loguru import logger
from sqlalchemy import Connection, insert, select, true, update

from population_restorator.db.entities import (
    t_population_divided,
    t_social_groups_distribution,
    t_social_groups_probabilities,
)


func: Callable


def _fix_people_number(  # pylint: disable=too-many-locals,too-many-arguments
    conn: Connection,
    year: int,
    house_id: int,
    age: int,
    sg_id: int,
    current: int,
    probable: int,
    is_male: bool,
    rng: np.random.Generator,
) -> None:
    """Update number of people for better correspondence to the statistics."""
    if current > probable * 2:
        needed = probable * 1.5
    elif current + 2 < probable / 2:
        needed = probable / 1.5
    else:
        return
    needed = ceil(needed) if rng.integers(0, 1, 1, endpoint=True)[0] else floor(needed)

    statement = (
        select(
            t_social_groups_probabilities.c.id,
            (t_social_groups_distribution.c.men_sg if is_male else t_social_groups_distribution.c.women_sg),
        )
        .select_from(t_social_groups_probabilities)
        .join(
            t_social_groups_distribution,
            t_social_groups_distribution.c.social_group_id == t_social_groups_probabilities.c.id,
        )
        .where(
            t_social_groups_distribution.c.age == age,
            (t_social_groups_distribution.c.men_sg if is_male else t_social_groups_distribution.c.women_sg) > 0,
            t_social_groups_probabilities.c.is_primary == true(),
            t_social_groups_probabilities.c.id != sg_id,
        )
    )
    sgs_ids: list[int] = []
    sgs_probs: list[int] = []
    for other_sg_id, probability in conn.execute(statement):
        sgs_ids.append(other_sg_id)
        sgs_probs.append(probability)

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
        else ([0], [abs(current - needed)])
    )

    for idx, change in zip(change_values[0], change_values[1]):
        needed_sg_id = sgs_ids[idx]
        statement = (
            update(t_population_divided)
            .values(
                **{
                    ("men" if is_male else "women"): (
                        t_population_divided.c.men if is_male else t_population_divided.c.women
                    )
                    + int(change)
                }
            )
            .where(
                t_population_divided.c.year == year,
                t_population_divided.c.house_id == house_id,
                t_population_divided.c.social_group_id == needed_sg_id,
                t_population_divided.c.age == age,
            )
        )
        if conn.execute(statement).rowcount == 0:
            statement = insert(t_population_divided).values(
                year=year,
                house_id=house_id,
                age=age,
                social_group_id=needed_sg_id,
                men=(int(change) if is_male else 0),
                women=(0 if is_male else int(change)),
            )
            conn.execute(statement)

        conn.execute(
            update(t_population_divided)
            .values(**{("men" if is_male else "women"): (needed)})
            .where(
                t_population_divided.c.year == year,
                t_population_divided.c.house_id == house_id,
                t_population_divided.c.age == age,
                t_population_divided.c.social_group_id == sg_id,
            )
        )


def balance_year_age_primary_social_groups(
    conn: Connection, year: int, age: int, houses_ids: list[int] | None, rng: np.random.Generator
) -> None:
    """Increase or decrease number of people with concrete primary social groups while preserving total
    number of people with set sex and age constant.
    """
    _probable_men = (t_population_divided.c.men * t_social_groups_distribution.c.men_sg).label("probable_men")
    _probable_women = (t_population_divided.c.women * t_social_groups_distribution.c.women_sg).label("probable_women")
    statement = (
        select(
            t_population_divided.c.house_id,
            t_population_divided.c.social_group_id,
            t_population_divided.c.men,
            t_population_divided.c.women,
            _probable_men,
            _probable_women,
        )
        .select_from(t_population_divided)
        .join(
            t_social_groups_probabilities, t_population_divided.c.social_group_id == t_social_groups_probabilities.c.id
        )
        .join(
            t_social_groups_distribution,
            (t_social_groups_distribution.c.social_group_id == t_social_groups_probabilities.c.id)
            & (t_social_groups_distribution.c.age == t_population_divided.c.age),
        )
        .where(
            t_social_groups_probabilities.c.is_primary == true(),
            t_population_divided.c.year == year,
            t_population_divided.c.age == age,
            (t_population_divided.c.men > _probable_men * 2)
            | (t_population_divided.c.men + 2 < _probable_men / 2)
            | (t_population_divided.c.women > _probable_women * 2)
            | (t_population_divided.c.women + 2 < _probable_women / 2),
        )
        .order_by(t_population_divided.c.house_id, t_population_divided.c.social_group_id)
    )
    for house_id, sg_id, men, women, probable_men, probable_women in conn.execute(statement).all():
        _fix_people_number(conn, year, house_id, age, sg_id, men, probable_men, True, rng)
        _fix_people_number(conn, year, house_id, age, sg_id, women, probable_women, False, rng)
