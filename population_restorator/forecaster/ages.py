"""Generic ages forecasting algorithm is defined here."""
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy import Engine, func, select, true

from population_restorator.db.entities import t_population_divided, t_social_groups_probabilities
from population_restorator.models import SurvivabilityCoefficients


func: Callable


@dataclass
class ForecastedAges:
    """Two dataframes (male and female) with index as year and columns as ages."""

    men: pd.DataFrame
    women: pd.DataFrame


def forecast_ages(  # pylint: disable=too-many-arguments,too-many-locals
    database: Engine,
    year_begin: int,
    year_end: int,
    boys_to_girls: float,
    survivability_coefficients: SurvivabilityCoefficients,
    fertility_coefficient: float,
    fertility_begin: int,
    fertility_end: int,
    houses_ids: list[int] | None = None,
) -> ForecastedAges:
    """Get modeled number of people for the given numeber of years based on set statistical parameters.

    If `houses_ids` is given, only houses with given ids will be used."""

    logger.debug("Obtaining number of people from the database")
    with database.connect() as conn:
        max_age: int = conn.execute(select(func.max(t_population_divided.c.age))).scalar_one()

        if max_age != len(survivability_coefficients.men):
            logger.warning(
                "Survivability coefficients age given for max age {}, but max age in the database is {}."
                " Using coefficients",
                len(survivability_coefficients.men),
                max_age,
            )
            max_age = len(survivability_coefficients.men)

        current_men, current_women = np.array([0] * (max_age + 1)), np.array([0] * (max_age + 1))
        cur = conn.execute(
            select(
                t_population_divided.c.age, func.sum(t_population_divided.c.men), func.sum(t_population_divided.c.women)
            )
            .select_from(t_population_divided)
            .join(
                t_social_groups_probabilities,
                t_population_divided.c.social_group_id == t_social_groups_probabilities.c.id,
            )
            .where(
                t_social_groups_probabilities.c.is_primary == true(),
                (t_population_divided.c.house_id.in_(houses_ids) if houses_ids is not None else true()),
            )
            .group_by(t_population_divided.c.age)
        )
        for age, men, women in cur:
            current_men[age] = men
            current_women[age] = women

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
