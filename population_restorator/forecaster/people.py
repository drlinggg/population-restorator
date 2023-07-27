"""Methods to forecast people are defined here."""
from __future__ import annotations

import sqlite3
import time
from typing import Iterable

import numpy as np
from loguru import logger

from population_restorator.forecaster.ages import ForecastedAges

from .balancing import balance_year_additional_social_groups, balance_year_age_sex, balance_year_primary_social_groups


def _log_year_results(cur: sqlite3.Cursor, year_shift: int) -> None:
    """Send current year population in the logger debug sink."""
    cur.execute(
        "SELECT sum(people) AS people"
        " FROM population_divided pd JOIN social_groups sg ON pd.social_group_id = sg.id"
        " WHERE sg.is_primary = true AND is_male = true"
    )
    men_year = cur.fetchone()[0]
    cur.execute(
        "SELECT sum(people) AS people"
        " FROM population_divided pd JOIN social_groups sg ON pd.social_group_id = sg.id"
        " WHERE sg.is_primary = true AND is_male = false"
    )
    women_year = cur.fetchone()[0]
    cur.execute(
        "SELECT sum(people) AS people"
        " FROM population_divided pd JOIN social_groups sg ON pd.social_group_id = sg.id"
        " WHERE sg.is_primary = false"
    )
    additionals = cur.fetchone()[0]

    logger.info(
        "Year 0+{} men population: {}, female: {}. Total additional social groups count: {}",
        year_shift,
        men_year,
        women_year,
        additionals,
    )


def forecast_people(
    start_db: sqlite3.Connection,
    forecasted_ages: ForecastedAges,
    years_databases: Iterable[sqlite3.Connection],
    rng: np.random.Generator | None = None,
) -> None:
    """Forecast people based on a people division on the start_year, saving each year in its own SQLite database opened
    by the given iterable `years_databases`
    """
    if rng is None:
        rng = np.random.default_rng(seed=int(time.time()))

    prev_cur: sqlite3.Cursor = start_db.cursor()

    prev_cur.execute("SELECT max(age) FROM population_divided")
    max_age = prev_cur.fetchone()[0]

    prev_cur.close()

    previous_db = start_db
    for i, year_db in enumerate(years_databases, 1):
        with previous_db, year_db:
            prev_cur: sqlite3.Cursor = previous_db.cursor()
            year_cur: sqlite3.Cursor = year_db.cursor()

            logger.debug(
                "Cloning year 0+{} database",
                i,
            )
            for line in previous_db.iterdump():
                if line not in ("BEGIN TRANSACTION;", "COMMIT;"):
                    year_cur.execute(line)

            year_cur.execute("SELECT sum(people) FROM population_divided WHERE age = 0")
            assert (year_cur.fetchone()[0] or 0) != 0
            year_cur.execute("UPDATE population_divided SET age = age + ?", (max_age + 1,))
            year_cur.execute("UPDATE population_divided SET age = age - ?", (max_age,))
            year_cur.execute("DELETE FROM population_divided WHERE age = ?", (max_age + 1,))
            year_cur.execute("SELECT sum(people) FROM population_divided WHERE age = 0")
            assert (year_cur.fetchone()[0] or 0) == 0

            logger.debug("Forecasting year 0+{}", i)
            for j, age in enumerate(forecasted_ages.men.columns):
                men_needed = forecasted_ages.men.iat[i, j]
                women_needed = forecasted_ages.women.iat[i, j]
                balance_year_age_sex(year_cur, age, men_needed, True, rng)
                balance_year_age_sex(year_cur, age, women_needed, False, rng)

            balance_year_primary_social_groups(year_cur, rng)
            balance_year_additional_social_groups(year_cur, rng)

            _log_year_results(year_cur, i)
