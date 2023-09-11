"""Age-sex balancing methods are defined here."""
from typing import Callable

import numpy as np
from loguru import logger
from sqlalchemy import Connection, func, insert, select, text, true, update

from population_restorator.db.entities import (
    t_houses_tmp,
    t_population_divided,
    t_social_groups_distribution,
    t_social_groups_probabilities,
)


func: Callable


def _increase_population(  # pylint: disable=too-many-arguments,too-many-locals
    conn: Connection, age: int, increase_needed: int, is_male: bool, year: int, rng: np.random.Generator
) -> None:
    """Add people of the given age and sex to the houses."""
    _load = (
        func.coalesce(func.sum(t_population_divided.c.men if is_male else t_population_divided.c.women), text("0"))
        / t_houses_tmp.c.capacity
    ).label("load")
    statement = (
        select(t_houses_tmp.c.id, _load)
        .select_from(t_houses_tmp)
        .join(t_population_divided, t_population_divided.c.house_id == t_houses_tmp.c.id, isouter=True)
        .join(
            t_social_groups_probabilities, t_population_divided.c.social_group_id == t_social_groups_probabilities.c.id
        )
        .where(t_population_divided.c.year == year, t_social_groups_probabilities.c.is_primary == true())
        .group_by(t_houses_tmp.c.id, t_houses_tmp.c.capacity)
        .having(_load > 0)
    )
    # pylint: disable=unnecessary-direct-lambda-call
    houses_ids, houses_probs = (lambda loads: (list(loads.keys()), np.array(list(loads.values()))))(
        dict(conn.execute(statement).all())
    )

    _prob = (
        t_social_groups_probabilities.c.probability
        * (
            t_social_groups_distribution.c.men_probability
            if is_male
            else t_social_groups_distribution.c.women_probability
        )
    ).label("probability")
    statement = (
        select(
            t_social_groups_probabilities.c.id,
            _prob,
        )
        .select_from(t_social_groups_probabilities)
        .join(
            t_social_groups_distribution,
            t_social_groups_distribution.c.social_group_id == t_social_groups_probabilities.c.id,
        )
        .where(t_social_groups_probabilities.c.is_primary == true(), _prob > 0)
    )
    # pylint: disable=unnecessary-direct-lambda-call
    sgs_ids, sgs_probs = (lambda probs: (list(probs.keys()), np.array(list(probs.values()))))(
        dict(conn.execute(statement).all())
    )

    total_probs = np.array((np.mat(houses_probs).T * sgs_probs).flat)
    total_probs /= total_probs.sum()

    change_values = np.unique(
        rng.choice(list(range(len(houses_ids) * len(sgs_ids))), increase_needed, replace=True, p=total_probs),
        return_counts=True,
    )
    for idx, change in zip(change_values[0], change_values[1]):
        house_id = houses_ids[idx // len(sgs_ids)]
        sg_id = sgs_ids[idx % len(sgs_ids)]
        updated = conn.execute(
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
                t_population_divided.c.social_group_id == sg_id,
                t_population_divided.c.age == age,
            )
        ).rowcount
        if updated == 0:
            conn.execute(
                insert(t_population_divided).values(
                    year=year,
                    house_id=house_id,
                    social_group_id=sg_id,
                    age=age,
                    **{("men" if is_male else "women"): int(change), ("women" if is_male else "men"): 0},
                )
            )


def _decrease_population(  # pylint: disable=too-many-arguments
    conn: Connection, age: int, decrease_needed: int, is_male: bool, year: int, rng: np.random.Generator
) -> None:
    """Remove people of the given age and sex from houses."""
    statement = (
        select(
            t_population_divided.c.house_id,
            t_social_groups_probabilities.c.id,
            func.sum(
                (t_population_divided.c.men if is_male else t_population_divided.c.women)
                * (1 - t_social_groups_probabilities.c.probability)
            ),
        )
        .select_from(t_population_divided)
        .join(
            t_social_groups_probabilities, t_population_divided.c.social_group_id == t_social_groups_probabilities.c.id
        )
        .where(t_population_divided.c.year == year, t_social_groups_probabilities.c.is_primary == true())
        .group_by(t_population_divided.c.house_id, t_social_groups_probabilities.c.id)
        .order_by(t_population_divided.c.house_id)
    )
    houses_sgs_ids = []
    houses_sgs_probs = []
    for house_id, sg_id, load in conn.execute(statement):
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
        conn.execute(
            update(t_population_divided)
            .values(
                **{
                    ("men" if is_male else "women"): (
                        t_population_divided.c.men if is_male else t_population_divided.c.women
                    )
                    - int(change)
                }
            )
            .where(
                t_population_divided.c.year == year,
                t_population_divided.c.house_id == house_id,
                t_population_divided.c.social_group_id == sg_id,
                t_population_divided.c.age == age,
            )
        )
    conn.execute(
        update(t_population_divided)
        .values(**{("men" if is_male else "women"): 0})
        .where((t_population_divided.c.men if is_male else t_population_divided.c.women) < 0)
    )


def balance_year_age(  # pylint: disable=too-many-arguments
    conn: Connection,
    age: int,
    men_needed: int,
    women_needed: int,
    year: int,
    houses_ids: list[int] | None,
    rng: np.random.Generator,
    max_tries_per_year: int = 20,
) -> None:
    """Increase or decrease population of houses to get needed summary number of people of the given age and sex.

    Args:
        conn (sqlalchemy.Connection): database connection
        age (int): age of people to be balanced
        men_needed (int): number of men needed exactly by statistics
        women_needed (int): number of women needed exactly by statistics
        year (int): year of balancing
        houses_ids (list[int] | None): identifier of houses to use
        rng (numpy.random.Generator): generator to keep the same resutls between launches
        max_tries_per_year (int, optional): number of attempts to balance accurately (used when population decrease
        is needed and wrong houses were used too many times). Defaults to 15.
    """
    for _ in range(max_tries_per_year):
        statement = (
            select(func.sum(t_population_divided.c.men), func.sum(t_population_divided.c.women))
            .select_from(t_population_divided)
            .join(
                t_social_groups_probabilities,
                t_population_divided.c.social_group_id == t_social_groups_probabilities.c.id,
            )
            .where(
                t_population_divided.c.year == year,
                t_population_divided.c.age == age,
                (t_population_divided.c.house_id.in_(houses_ids) if houses_ids is not None else true()),
                t_social_groups_probabilities.c.is_primary == true(),
            )
        )
        men_in_db, women_in_db = map(lambda x: x or 0, conn.execute(statement).one())
        if men_in_db == men_needed and women_in_db == women_needed:
            return

        logger.trace("Age {}: men {} -> {}, women {} -> {}", age, men_in_db, men_needed, women_in_db, women_needed)
        if men_in_db < men_needed:
            _increase_population(conn, age, men_needed - men_in_db, True, year, rng)
        elif men_in_db > men_needed:
            _decrease_population(conn, age, men_in_db - men_needed, True, year, rng)

        if women_in_db < women_needed:
            _increase_population(conn, age, women_needed - women_in_db, False, year, rng)
        elif women_in_db > women_needed:
            _decrease_population(conn, age, women_in_db - women_needed, False, year, rng)

    logger.warning(
        "Could not balance people of age {} (men {} -> {}, women {} -> {}) by {} tries",
        age,
        men_in_db,
        men_needed,
        women_in_db,
        women_needed,
        max_tries_per_year,
    )
