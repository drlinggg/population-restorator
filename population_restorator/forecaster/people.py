"""Methods to forecast people are defined here."""
from __future__ import annotations

import multiprocessing as mp
import time
from typing import Callable, Iterable

import numpy as np
from loguru import logger
from sqlalchemy import Connection, Engine, create_engine, delete, false, func, insert, select, true

from population_restorator.db.entities import t_population_divided, t_social_groups_probabilities
from population_restorator.db.ops import prepare_db
from population_restorator.forecaster.ages import ForecastedAges

from .balancing import balance_year_additional_social_groups, balance_year_age, balance_year_age_primary_social_groups


func: Callable


def _balance_year_age(  # pylint: disable=too-many-arguments
    engine: Engine,
    territory_id: int,
    year: int,
    age: int,
    men_needed: int,
    women_needed: int,
    houses_ids: list[int] | None,
    rng: np.random.Generator,
) -> None:
    """Perform forecasting people balancing of a given year and age in a temporary database"""
    logger.debug("Forecasting year {} - age {}", year, age)

    with engine.connect() as conn:
        balance_year_age(conn, territory_id, age, men_needed, women_needed, year, houses_ids, rng)
        balance_year_age_primary_social_groups(conn, year, age, houses_ids, rng)
        balance_year_additional_social_groups(conn, year, age, houses_ids, rng)
        conn.commit()


def _balance_year_age_mp(  # pylint: disable=too-many-arguments
    conn_dsn: str,
    year: int,
    age: int,
    men_needed: int,
    women_needed: int,
    houses_ids: list[int] | None,
    rng: np.random.Generator,
) -> None:
    """Perform forecasting people balancing of a given year and age in a temporary database"""
    logger.debug("Forecasting year {} - age {}", year, age)

    engine = create_engine(conn_dsn)

    with engine.connect() as conn:
        balance_year_age(conn, age, men_needed, women_needed, year, houses_ids, rng)
        balance_year_age_primary_social_groups(conn, year, age, houses_ids, rng)
        balance_year_additional_social_groups(conn, year, age, houses_ids, rng)
        conn.commit()

    engine.dispose()


def _log_year_results(conn: Connection, territory_id: int, year: int) -> None:
    """Send current year population in the logger debug sink."""
    men_year, women_year = conn.execute(
        select(func.sum(t_population_divided.c.men), func.sum(t_population_divided.c.women))
        .select_from(t_population_divided)
        .join(
            t_social_groups_probabilities, t_population_divided.c.social_group_id == t_social_groups_probabilities.c.id
        ).where(t_population_divided.c.year == year,
               t_population_divided.c.territory_id == territory_id,
               t_social_groups_probabilities.c.is_primary == true())
    ).fetchone()

    additionals = conn.execute(
        select(func.sum(t_population_divided.c.men + t_population_divided.c.women))
        .select_from(t_population_divided)
        .join(
            t_social_groups_probabilities, t_population_divided.c.social_group_id == t_social_groups_probabilities.c.id
        )
        .where(t_population_divided.c.year == year,
               t_population_divided.c.territory_id == territory_id, 
               t_social_groups_probabilities.c.is_primary == false())
    ).scalar_one()

    logger.info(
        "Year {}, forecast for territory_id {}, men population: {}, female: {}. Total additional social groups count: {}",
        year,
        territory_id,
        men_year,
        women_year,
        additionals,
    )


#tobefixedterritory_id
def forecast_people(  # pylint: disable=too-many-locals,too-many-arguments
    start_engine: Engine,
    territory_id: int,
    forecasted_ages: ForecastedAges,
    years_dsns: Iterable[str],
    base_year: int,
    houses_ids: list[int] | None = None,
    rng: np.random.Generator | None = None,
    callback: Callable[[int, Engine]] | None = None,
    threads: int = 1,
) -> None:
    """Forecast people based on a people division on the start_year, saving each year in its own database connection
    opened by the given iterable `years_databases`.

    If the callback is given, after another year calculations are done, calls a given function with two arguments -
    current year finished and its database connection.

    If `houses_ids` is set, only houses with given ids will be forecasted (useful when the database already contains
    data for other cities for example).

    Threads parameter higher than 1 should only be used with temporary databases supporting simultanious access from
    multiple workers (not SQLite).
    """
    if rng is None:
        rng = np.random.default_rng(seed=int(time.time()))

    with start_engine.connect() as year_conn:
        max_age = year_conn.execute(
            select(func.max(t_population_divided.c.age)).where(t_population_divided.c.territory_id == territory_id)
        ).scalar_one()

    previous_engine = start_engine
    for i, year_dsn in enumerate(years_dsns, 1):
        year = base_year + i
        year_engine = create_engine(year_dsn)
        with year_engine.connect() as year_conn, previous_engine.connect() as prev_conn:
            prepare_db(year_conn, prev_conn)
            logger.debug(
                "Cloning year {} -> {} database",
                year - 1,
                year,
            )
            year_conn.execute(
                delete(t_population_divided).where(
                    t_population_divided.c.year == year,
                    t_population_divided.c.territory_id == territory_id,
                    (t_population_divided.c.house_id.in_(houses_ids) if houses_ids is not None else true()),
                )
            )
            statement = select(
                t_population_divided.c.house_id,
                t_population_divided.c.age,
                t_population_divided.c.social_group_id,
                t_population_divided.c.men,
                t_population_divided.c.women,
            ).where(
                t_population_divided.c.year == year - 1,
                t_population_divided.c.age != max_age,
                t_population_divided.c.territory_id == territory_id,
                (t_population_divided.c.house_id.in_(houses_ids) if houses_ids is not None else true()),
            )
            copied = False
            for house_id, age, social_group_id, men, women in prev_conn.execute(statement):
                copied = True
                year_conn.execute(
                    insert(t_population_divided).values(
                        year=year,
                        age=age + 1,
                        house_id=house_id,
                        social_group_id=social_group_id,
                        territory_id=territory_id,
                        men=men,
                        women=women,
                    )
                )
            year_conn.commit()
        if not copied:
            raise RuntimeError(f"Could not clone database of the year {year} - no population_divided entries found")

        if threads == 1:
            for j, age in enumerate(forecasted_ages.men.columns):
                men_needed = forecasted_ages.men.iat[i, j]
                women_needed = forecasted_ages.women.iat[i, j]
                _balance_year_age(year_engine, territory_id, year, age, men_needed, women_needed, houses_ids, rng) #??
        else:
            with mp.Pool(threads) as pool:
                pool.starmap(
                    _balance_year_age_mp,
                    [
                        (
                            year_dsn,
                            year,
                            age,
                            forecasted_ages.men.iat[i, j],
                            forecasted_ages.women.iat[i, j],
                            houses_ids,
                            rng,
                        )
                        for j, age in enumerate(forecasted_ages.men.columns)
                    ],
                )

        with year_engine.connect() as year_conn:
            _log_year_results(year_conn, territory_id, year)

        if callback is not None:
            callback(year_dsn, year)

        year_engine.dispose()

        previous_engine = year_engine
