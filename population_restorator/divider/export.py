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
    territory_id: int,
    distribution: pd.Series,
    #houses_capacity: pd.Series,
    houses_df: pd.DataFrame,
    distribution_probabilities: SocialGroupsDistribution,
    year: int,
    verbose: bool = False,
) -> None:
    """Save the given people division to the database.

    Args:
        conn (sqlalchemy.Connection): connection to the database to save results to.
        territory_id (int): The territory ID to associate with these records.
        distribution (pandas.Series): people distribution as pandas Series with numpy.ndarray as values
        houses_capacity (pandas.Series): capacity value for each house
        distribution_probabilities (SocialGroupsDistribution): probability distribution by social_groups-sex-age
        year (int): year to save distribution for
        verbose (bool, optional): print progress bar. Defaults to False.
    """
    func = distribution_probabilities.get_resulting_function()

    houses_df.set_index('house_id',drop=False, inplace=True)

    if distribution.shape[0] == 0:
        logger.warning("Requested to save an empty people division. Exiting without writing database.")
        return

    with conn:
        prepare_db(conn)

        for house_id in houses_df.index:
            living_area = houses_df["living_area"][house_id]
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
        deleted_buildings = conn.execute(
            delete(t_population_divided).where(
                t_population_divided.c.year == year,
                t_population_divided.c.house_id.in_(distribution.index.to_list()),
                t_population_divided.c.territory_id == territory_id  # Удаляем только записи для текущей территории
            )
        ).rowcount

        if deleted_buildings > 0:
            logger.debug(f"Deleted {deleted_buildings} buildings already present for territory {territory_id}")

        for house_id, distribution_array in iterable:
            statement = insert(t_population_divided).values(
                year=year,
                house_id=house_id,
                territory_id=territory_id,  # Добавляем territory_id
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
                            "territory_id": territory_id,
                            "men": men,
                            "women": women,
                        }
                        for age, (men, women) in enumerate(zip(people_division.men, people_division.women))
                        if men > 0 or women > 0
                    ]
                )
            if len(statement_values) > 0:
                conn.execute(statement, statement_values)

        conn.commit()
