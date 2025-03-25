"""Database preparation steps are defined here."""
from __future__ import annotations

from typing import Callable

from sqlalchemy import Connection, Index, distinct, func, insert, select, update
from sqlalchemy.schema import CreateIndex, CreateTable

from population_restorator.db.entities import (
    t_houses_tmp,
    t_population_divided,
    t_social_groups_distribution,
    t_social_groups_probabilities,
)


func: Callable


def update_sgs_distribution(conn: Connection) -> None:
    """Perform a men_sg and women_sg recalculation"""
    sgd_inner = t_social_groups_distribution.alias("sgd_inner")
    sgs_inner = t_social_groups_probabilities.alias("sgs_inner")
    to_update = t_social_groups_distribution.alias("sgd_to_update")
    conn.execute(
        update(to_update)
        .values(
            men_sg=to_update.c.men_probability
            / select(func.sum(sgd_inner.c.men_probability))
            .select_from(sgd_inner)
            .join(t_social_groups_probabilities, sgd_inner.c.social_group_id == t_social_groups_probabilities.c.id)
            .join(sgs_inner, to_update.c.social_group_id == sgs_inner.c.id)
            .where(
                sgd_inner.c.age == to_update.c.age, t_social_groups_probabilities.c.is_primary == sgs_inner.c.is_primary
            )
            .scalar_subquery()
        )
        .where(to_update.c.men_probability != 0)
    )
    conn.execute(
        update(to_update)
        .values(
            women_sg=to_update.c.women_probability
            / select(func.sum(sgd_inner.c.women_probability))
            .select_from(sgd_inner)
            .join(t_social_groups_probabilities, sgd_inner.c.social_group_id == t_social_groups_probabilities.c.id)
            .join(sgs_inner, to_update.c.social_group_id == sgs_inner.c.id)
            .where(
                sgd_inner.c.age == to_update.c.age, t_social_groups_probabilities.c.is_primary == sgs_inner.c.is_primary
            )
            .scalar_subquery()
        )
        .where(to_update.c.women_probability != 0)
    )


def prepare_db(conn: Connection, prev_conn: Connection | None = None) -> None:
    """Create tables required for population_restorator to work with.

    If `prev_conn` is set, ensures that social_groups and houses data is copied (check is performed only by
    identifiers)."""
    conn.execute(CreateTable(t_social_groups_probabilities, if_not_exists=True))
    conn.execute(CreateTable(t_social_groups_distribution, if_not_exists=True))
    conn.execute(CreateTable(t_houses_tmp, if_not_exists=True))
    conn.execute(CreateTable(t_population_divided, if_not_exists=True))
    conn.execute(
        CreateIndex(
            Index(
                "population_divided_house_age_social_group",
                t_population_divided.c.year,
                t_population_divided.c.house_id,
                t_population_divided.c.age,
                t_population_divided.c.social_group_id,
                t_population_divided.c.territory_id,
                unique=True,
            ),
            if_not_exists=True,
        ),
    )



    if prev_conn is not None:
        social_groups_present = set(conn.execute(select(distinct(t_social_groups_probabilities.c.id))).scalars())
        for sg_id, name, probability, is_primary in prev_conn.execute(
            select(
                t_social_groups_probabilities.c.id,
                t_social_groups_probabilities.c.name,
                t_social_groups_probabilities.c.probability,
                t_social_groups_probabilities.c.is_primary,
            )
        ):
            if sg_id not in social_groups_present:
                conn.execute(
                    insert(t_social_groups_probabilities).values(
                        id=sg_id, name=name, probability=probability, is_primary=is_primary
                    )
                )

        sgs_distribution_present = set(
            conn.execute(select(t_social_groups_distribution.c.social_group_id, t_social_groups_distribution.c.age))
        )
        sgd_edited = False
        for sg_id, age, men_prob, women_prob in prev_conn.execute(
            select(
                t_social_groups_distribution.c.social_group_id,
                t_social_groups_distribution.c.age,
                t_social_groups_distribution.c.men_probability,
                t_social_groups_distribution.c.women_probability,
            )
        ):
            if (sg_id, age) not in sgs_distribution_present:
                conn.execute(
                    insert(t_social_groups_distribution).values(
                        social_group_id=sg_id, age=age, men_probability=men_prob, women_probability=women_prob
                    )
                )
                sgd_edited = True
        if sgd_edited:
            update_sgs_distribution(conn)

        houses_present = set(conn.execute(select(distinct(t_houses_tmp.c.id))).scalars())
        for house_id, capacity in prev_conn.execute(select(t_houses_tmp.c.id, t_houses_tmp.c.capacity)):
            if house_id not in houses_present:
                conn.execute(insert(t_houses_tmp).values(id=house_id, capacity=capacity))
