"""Balance command-line utility configuration is defined here."""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import pandas as pd
from loguru import logger
from rich.console import Console
from sqlalchemy import create_engine

from population_restorator.forecaster import forecast_ages, forecast_people


def forecast(  # pylint: disable=too-many-arguments,too-many-locals
    houses_db: str,
    territory_id: int,
    coeffs,
    year_begin: int,
    years: int,
    boys_to_girls: float,
    fertility_coefficient: float,
    fertility_begin: int,
    fertility_end: int,
    verbose: bool,
) -> None: # not none
    """Forecast population change considering division.

    Model population change for the given number of years based on a given statistical parameters.
    """
    console = Console(highlight=False, emoji=False)

    try:
        database = create_engine(f"sqlite:///{str(houses_db)}")
    except Exception as exc:  # pylint: disable=broad-except
        logger.critical("Exception on reading input data: {!r}", exc)
        if verbose:
            traceback.print_exc()
        sys.exit(1)

    forecasted_ages = forecast_ages(
        database=database,
        territory_id=territory_id,
        year_begin=year_begin,
        year_end=year_begin + years,
        boys_to_girls=boys_to_girls,
        survivability_coefficients=coeffs,
        fertility_coefficient=fertility_coefficient,
        fertility_begin=fertility_begin,
        fertility_end=fertility_end,
    )

    if verbose:
        console.print(
            "[blue]men:\n{}[/blue]".format(  # pylint: disable=consider-using-f-string
                forecasted_ages.men.join(pd.Series(forecasted_ages.men.apply(sum, axis=1), name="sum"))
            )
        )
        console.print(
            "[bright_magenta]women:\n{}[/bright_magenta]".format(  # pylint: disable=consider-using-f-string
                forecasted_ages.women.join(pd.Series(forecasted_ages.women.apply(sum, axis=1), name="sum"))
            )
        )

    output_dir = "/home/banakh/shitstorage/"

    db_names = [str(output_dir + f"year_{year}.sqlite") for year in range(year_begin + 1, year_begin + years + 1)]
    if any(Path(db_name).exists() for db_name in db_names):
        console.print(
            "[red]Error: forecasted SQLite tables already exist in the diven directory"
            f" [b]'{output_dir}'[/b], aborting[/red]"
        )
        sys.exit(1)
  
    databases = (f"sqlite:///{db_name}" for db_name in db_names)

    forecast_people(database,
        territory_id=territory_id,
        forecasted_ages=forecasted_ages,
        years_dsns=databases,
        base_year=year_begin
    )
