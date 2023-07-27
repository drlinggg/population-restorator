"""Generic ages forecasting algorithm is defined here."""
import sqlite3
from dataclasses import dataclass

import numpy as np
import pandas as pd
from loguru import logger

from population_restorator.models import SurvivabilityCoefficients


@dataclass
class ForecastedAges:
    """Two dataframes (male and female) with index as year and columns as ages."""

    men: pd.DataFrame
    women: pd.DataFrame


def forecast_ages(  # pylint: disable=too-many-arguments,too-many-locals
    database: sqlite3.Connection,
    year_begin: int,
    year_end: int,
    boys_to_girls: float,
    survivability_coefficients: SurvivabilityCoefficients,
    fertility_coefficient: float,
    fertility_begin: int,
    fertility_end: int,
) -> ForecastedAges:
    """Get modeled number of people for the given numeber of years based on set statistical parameters."""
    cur = database.cursor()

    logger.debug("Obtaining number of people from the database")
    try:
        cur.execute("SELECT max(age) FROM population_divided")
        max_age: int = cur.fetchone()[0]

        if max_age != len(survivability_coefficients.men):
            raise ValueError(
                f"Survivability coefficients age given for {len(survivability_coefficients.men) + 1} ages, but max"
                f" age in the database is {max_age}"
            )

        current_men, current_women = np.array([0] * (max_age + 1)), np.array([0] * (max_age + 1))
        cur.execute(
            "SELECT age, is_male, sum(people)"
            " FROM population_divided p"
            "   JOIN social_groups sg ON p.social_group_id = sg.id"
            " WHERE sg.is_primary = true"
            " GROUP BY age, is_male"
        )
        for age, is_male, people in cur:
            if is_male:
                current_men[age] = people
            else:
                current_women[age] = people

    finally:
        cur.close()

    logger.debug("Forecasting people divided by sex and age")

    res_men = [current_men.copy()]
    res_women = [current_women.copy()]

    for _ in range(year_begin, year_end):
        fertil_women = current_women[fertility_begin : fertility_end + 1].sum()

        current_men: np.ndarray[int] = np.concatenate(
            [[0], (current_men[:-1] * survivability_coefficients.men).round().astype(int)]
        )
        current_women: np.ndarray[int] = np.concatenate(
            [[0], (current_women[:-1] * survivability_coefficients.women).round().astype(int)]
        )

        current_men[0] = fertil_women * fertility_coefficient / 2 * boys_to_girls
        current_women[0] = fertil_women * fertility_coefficient / 2 * (1 / boys_to_girls)

        res_men.append(current_men.copy())
        res_women.append(current_women.copy())

    return ForecastedAges(
        pd.DataFrame(res_men, index=range(year_begin, year_end + 1), columns=range(max_age + 1)),
        pd.DataFrame(res_women, index=range(year_begin, year_end + 1), columns=range(max_age + 1)),
    )
