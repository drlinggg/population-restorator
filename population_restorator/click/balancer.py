"""Balance command-line utility configuration is defined here."""
from __future__ import annotations

import itertools
import sys
import traceback

import click
import pandas as pd
from loguru import logger

from population_restorator.balancer import balance_houses, balance_territories
from population_restorator.utils import read_file
from population_restorator.utils.data_saver import to_file
from population_restorator.utils.data_structure import city_as_territory

from .main_group import main


@main.command("balance")
@click.option(
    "--total_population",
    "-dp",
    type=int,
    help="Total population value for the given city",
    required=True,
)
@click.option(
    "--inner_territories",
    "-di",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the inner territories file (.json, .geojson, .xlsx and .csv are supported),"
    " must contain 'name' (str) and optionally 'population' (int) columns",
    required=True,
)
@click.option(
    "--outer_territories",
    "-do",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the outer territories file (.json, .gejson, .xlsx and .csv are fine),"
    " must contain 'name' (str) and optionally 'population' (int) columns",
    required=True,
)
@click.option(
    "--houses",
    "-dh",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the houses (dwellings) file (.json, .gejson, .xlsx and .csv are fine),"
    " must contain 'living_area' (float), 'outer_territory' (str) and 'inner_territory' (str) columns",
    required=True,
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Increase logger verbosity to DEBUG and print some additional stataments"
)
@click.option(
    "--outer_territories_output",
    "-oo",
    type=click.UNPROCESSED,
    metavar="Path",
    help="Filename for a balanced outer territories export (.json, .xlsx and .csv formats are supported)",
    default=None,
    show_default=True,
)
@click.option(
    "--inner_territories_output",
    "-oi",
    type=click.UNPROCESSED,
    metavar="Path",
    help="Filename for a balanced inner territories export (.json, .xlsx and .csv formats are supported)",
    default=None,
    show_default=True,
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False),
    help="Filename for a populated buildings export (.json, .geojson, .xlsx and .csv formats are supported)",
    default="houses_balanced.csv",
    show_default=True,
)
def balance(  # pylint: disable=too-many-arguments,too-many-locals
    total_population: int,
    inner_territories: str,
    outer_territories: str,
    houses: str,
    verbose: bool,
    inner_territories_output: str | None,
    outer_territories_output: str | None,
    output: str,
) -> None:
    """Balance dwellings total population

    Balance population for the given city provided with total population (accurate value), populations of inner and
    outer territory units (optional), list of buildings with living area value, and probability values of a person
    sex, age and social group.
    """
    if inner_territories_output is not None:
        if inner_territories_output.lower().endswith(".geojson"):
            logger.error("Unable to export balanced inner territories as geojson, use .csv, .xlsx or .json instead")
            sys.exit(1)

    if outer_territories_output is not None:
        if outer_territories_output.lower().endswith(".geojson"):
            logger.error("Unable to export balanced inner territories as geojson, use .csv, .xlsx or .json instead")
            sys.exit(1)

    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")
    try:
        ot_df = read_file(outer_territories)
        it_df = read_file(inner_territories)
        houses_df = read_file(houses)
    except Exception as exc:  # pylint: disable=broad-except
        logger.critical("Exception on reading input data: {!r}", exc)
        if verbose:
            traceback.print_exc()
        sys.exit(1)

    try:
        city = city_as_territory(total_population, ot_df, it_df, houses_df)
    except Exception as exc:  # pylint: disable=broad-except
        logger.critical("Exception on representing city as territory: {!r}", exc)
        if verbose:
            traceback.print_exc()
        sys.exit(1)

    if verbose:
        from rich import print as rich_print  # pylint: disable=import-outside-toplevel

        rich_print("[i]City model information before balancing:[/i]")
        rich_print(city.deep_info())

    logger.info("Balancing city territories")
    balance_territories(city)

    logger.info("Balancing city houses")
    balance_houses(city)

    if outer_territories_output is not None:
        logger.opt(colors=True).info("Exporing outer_territories to file <cyan>{}</cyan>", outer_territories_output)
        outer_territories_new_df = pd.DataFrame(
            (
                {
                    "name": ot.name,
                    "population": ot.population,
                    "inner_territories_population": ot.get_total_territories_population(),
                    "houses_number": ot.get_all_houses().shape[0],
                    "houses_population": ot.get_total_houses_population(),
                    "total_living_area": ot.get_total_living_area(),
                }
                for ot in city.inner_territories
            )
        )
        to_file(outer_territories_new_df, outer_territories_output)

    if inner_territories_output is not None:
        logger.opt(colors=True).info("Exporing inner_territories to file <cyan>{}</cyan>", inner_territories_output)
        inner_territories_new_df = pd.DataFrame(
            itertools.chain.from_iterable(
                (
                    {
                        "name": it.name,
                        "population": it.population,
                        "inner_territories_population": it.get_total_territories_population(),
                        "houses_number": it.get_all_houses().shape[0],
                        "houses_population": it.get_total_houses_population(),
                        "total_living_area": it.get_total_living_area(),
                    }
                    for it in ot.inner_territories
                )
                for ot in city.inner_territories
            )
        )
        to_file(inner_territories_new_df, inner_territories_output)

    logger.opt(colors=True).info("Saving to file <cyan>{}</cyan>", output)
    to_file(city.get_all_houses(), output)
