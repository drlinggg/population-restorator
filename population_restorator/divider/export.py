"""People division methods are defined here."""
from __future__ import annotations

import itertools

import pandas as pd
from loguru import logger
from sqlalchemy import Connection, delete, insert, select, update
from tqdm import tqdm

from population_restorator.db.entities import (
    t_houses_tmp,
    t_population_divided,
    t_social_groups_distribution,
    t_social_groups_probabilities,
)
from population_restorator.db.ops import prepare_db
from population_restorator.db.ops.preparation import update_sgs_distribution
from population_restorator.models.social_groups import SocialGroupsDistribution


def save_houses_distribution_to_db(  # pylint: disable=too-many-locals,too-many-branches,too-many-arguments
    conn: Connection,
    distribution: pd.Series,
    houses_capacity: pd.Series,
    distribution_probabilities: SocialGroupsDistribution,
    year: int,
    verbose: bool = False,
) -> None:
    """Save the given people division to the database.

    Args:
        conn (sqlalchemy.Connection): connection to the database to save results to.
        distribution (pandas.Series): people distribution as pandas Series with numpy.ndarray as values
        houses_capacity (pandas.Series): capacity value for each house
        distribution_probabilities (SocialGroupsDistribution): probability distribution by social_groups-sex-age
        year (int): year to save distribution for
        verbose (bool, optional): print progress bar. Defaults to False.
    """
    func = distribution_probabilities.get_resulting_function()

    if distribution.shape[0] == 0:
        logger.warning("Requested to save an empty people division. Exiting without writing database.")
        return

    with conn:
        prepare_db(conn)

        for house_id, living_area in houses_capacity.items():
            updated = conn.execute(
                update(t_houses_tmp).values(capacity=living_area).where(t_houses_tmp.c.id == house_id)
            ).rowcount

            if updated == 0:
                conn.execute(insert(t_houses_tmp).values(id=house_id, capacity=living_area))

        social_groups_ids = {}
        for is_primary, social_group in itertools.chain(
            zip(itertools.repeat(True), distribution_probabilities.primary),
            zip(itertools.repeat(False), distribution_probabilities.additional),
        ):
            idx = conn.execute(
                select(t_social_groups_probabilities.c.id).where(
                    t_social_groups_probabilities.c.name == social_group.name
                )
            ).scalar_one_or_none()
            if idx is None:
                idx = conn.execute(
                    insert(t_social_groups_probabilities)
                    .values(name=social_group.name, probability=float(social_group.probability), is_primary=is_primary)
                    .returning(t_social_groups_probabilities.c.id),
                ).scalar_one()
                for age, men, women in zip(
                    itertools.count(), social_group.distribution.men, social_group.distribution.women
                ):
                    conn.execute(
                        insert(t_social_groups_distribution).values(
                            social_group_id=idx, age=age, men_probability=float(men), women_probability=float(women)
                        )
                    )
            social_groups_ids[social_group.name] = idx
        update_sgs_distribution(conn)

        iterable = (
            tqdm(distribution.items(), total=len(distribution), desc=f"Saving houses year={year}")
            if verbose
            else iter(distribution.items())
        )
        # statements_rows = 0
        # statements_execute = 0
        deleted_buildings = conn.execute(
            delete(t_population_divided).where(
                t_population_divided.c.year == year, t_population_divided.c.house_id.in_(distribution.index.to_list())
            )
        ).rowcount

        if deleted_buildings > 0:
            logger.debug("Deleted {} buildings already present", deleted_buildings)
        for house_id, distribution_array in iterable:
            statement = insert(t_population_divided).values(
                year=year,
                house_id=house_id,
            )
            statement_values: list[dict] = []

            for social_group_name, people_division in func(distribution_array).items():
                social_group_id = social_groups_ids.get(social_group_name)
                if social_group_id is None:
                    raise ValueError(
                        f"Could not insert people division because social group '{social_group_name}' is not present"
                    )

                statement_values.extend(
                    [
                        {
                            "social_group_id": social_group_id,
                            "age": age,
                            "men": men,
                            "women": women,
                        }
                        for age, (men, women) in enumerate(zip(people_division.men, people_division.women))
                        if men > 0 or women > 0
                    ]
                )

            # statements_execute += 1
            # statements_rows += len(statement_values)
            if len(statement_values) > 0:
                conn.execute(statement, statement_values)

        # print(f"Total number of statements - {statements_execute}, rows to be inserted - {statements_rows}")
        # from sqlalchemy.dialects import postgresql

        # print(f"execute_example:\n{statement.compile(dialect=postgresql.dialect())}")
        # raise NotImplementedError()
        conn.commit()
