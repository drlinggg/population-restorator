"""Balance command-line utility configuration is defined here."""
from __future__ import annotations

import datetime
import sys

import pandas as pd
from loguru import logger
from sqlalchemy import create_engine

from population_restorator.divider import divide_houses, save_houses_distribution_to_db
from population_restorator.models.parse.social_groups import SocialGroupsDistribution

def divide(  # pylint: disable=too-many-arguments,too-many-locals
    territory_id: int,
    houses_df: pd.DataFrame,
    distribution: SocialGroupsDistribution,
    year: int | None,
    verbose: bool,
    working_db_path: str = ""
) -> tuple[pd.DataFrame, pd.Series]:
    """Divide dwellings people by sex, age and social group

    Model houses population sex and age parameters based on given social_groups distribution.
    The distribution is given in json format as an object with single 'social_groups' key containing a list of social
    group objects, each of them having keys: 'name', 'ages_men', 'ages_women', and optionally 'total' and
    'is_additional' with default value of False.

    'total' attribute can be absolute (number of people) or relative (number of people of social group divided by
    total).
    'ages' list can the same way contain absolute or relative numbers, but absolute must sum up to 'total' if it is also
    set in absolute form.
    """

    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    if year is None:
        year = datetime.datetime.now().year
        logger.opt(colors=True).info("Using <cyan>{}</cyan> as a year to save a forecast", year)

    logger.info("Dividing houses ({}) population", len(houses_df))
    distribution_series = pd.Series(
        divide_houses(houses_df["population"].astype(int).to_list(), distribution), index=houses_df.house_id
    )

    logger.info("Saving results to {}", working_db_path)
    engine = create_engine(f"sqlite:///{working_db_path}")

    save_houses_distribution_to_db(
        engine.connect(),
        territory_id,
        distribution_series,
        houses_df,
        distribution,
        year,
        verbose,
    )

    return (houses_df, distribution_series)
