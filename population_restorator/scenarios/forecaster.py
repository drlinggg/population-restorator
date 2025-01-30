"""Balance command-line utility configuration is defined here."""
from __future__ import annotations

import datetime
import sys
import traceback
from pathlib import Path

import pandas as pd
from loguru import logger
from rich.console import Console
from sqlalchemy import create_engine

from population_restorator.forecaster import forecast_ages, forecast_people
from population_restorator.models.parse import read_coefficients

def forecast(  # pylint: disable=too-many-arguments,too-many-locals
    houses_db: str,
    survivability_coefficients: str,
    year_begin: int | None,
    years: int,
    boys_to_girls: float,
    fertility_coefficient: float,
    fertility_begin: int,
    fertility_end: int,
    output_dir: Path,
    verbose: bool,
) -> None:
    """Forecast population change considering division.

    Model population change for the given number of years based on a given statistical parameters.
    """
    console = Console(highlight=False, emoji=False)

    coeffs = read_coefficients(str(survivability_coefficients))

    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    if year_begin is None:
        year_begin = datetime.datetime.now().year
        console.print(f"Using [cyan]{year_begin}[/cyan] as a year to start a forecast")

    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True)
        except OSError as exc:
            console.print(f"[red]Could not create an output directory '{output_dir}'[/red]: {exc!r}")

    try:
        database = create_engine(f"sqlite:///{str(houses_db)}")
    except Exception as exc:  # pylint: disable=broad-except
        logger.critical("Exception on reading input data: {!r}", exc)
        if verbose:
            traceback.print_exc()
        sys.exit(1)

    forecasted_ages = forecast_ages(
        database,
        year_begin,
        year_begin + years,
        boys_to_girls,
        coeffs,
        fertility_coefficient,
        fertility_begin,
        fertility_end,
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

    db_names = [str(output_dir / f"year_{year}.sqlite") for year in range(year_begin + 1, year_begin + years + 1)]
    if any(Path(db_name).exists() for db_name in db_names):
        console.print(
            "[red]Error: forecasted SQLite tables already exist in the diven directory"
            f" [b]'{output_dir}'[/b], aborting[/red]"
        )
        sys.exit(1)

    databases = (f"sqlite:///{db_name}" for db_name in db_names)

    forecast_people(database, forecasted_ages, databases, year_begin)
