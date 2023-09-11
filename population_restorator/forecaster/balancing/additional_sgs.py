"""Additional social_groups balancing methods are defined here."""
from __future__ import annotations

from math import ceil, floor
from typing import Callable

import numpy as np
from sqlalchemy import Connection, select, true, update

from population_restorator.db.entities import (
    t_population_divided,
    t_social_groups_distribution,
    t_social_groups_probabilities,
)


func: Callable


def balance_year_additional_social_groups(  # pylint: disable=too-many-locals
    conn: Connection, year: int, age: int, houses_ids: list[int] | None, rng: np.random.Generator
) -> None:
    """Find houses with the number of social groups highly different from the statistical
    distribution and balance them.
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
        if men > probable_men * 2:
            needed_men = probable_men * 1.5
        elif men < probable_men / 2:
            needed_men = probable_men / 1.5
        else:
            needed_men = men
        needed_men = ceil(needed_men) if rng.integers(0, 1, 1, endpoint=True)[0] else floor(needed_men)

        if women > probable_women * 2:
            needed_women = probable_women * 1.5
        elif women < probable_women / 2:
            needed_women = probable_women / 1.5
        else:
            needed_women = women
        needed_women = ceil(needed_women) if rng.integers(0, 1, 1, endpoint=True)[0] else floor(needed_women)

        conn.execute(
            update(t_population_divided)
            .values(men=needed_men, women=needed_women)
            .where(
                t_population_divided.c.year == year,
                t_population_divided.c.house_id == house_id,
                t_population_divided.c.age == age,
                t_population_divided.c.social_group_id == sg_id,
            )
        )
