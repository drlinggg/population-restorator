"""Balance command-line utility configuration is defined here."""
from __future__ import annotations

import sys
import traceback

import click
from loguru import logger

from population_restorator.utils import read_file
from population_restorator.utils.data_saver import to_file

from population_restorator.scenarios import balance as pbalance

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
    "--territories",
    "-di",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the inner territories file (.json, .geojson, .xlsx and .csv are supported),"
    " must contain 'name' (str) and optionally 'population' (int) columns",
    required=True,
)
@click.option(
    "--houses",
    "-dh",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the houses (dwellings) file (.json, .geojson, .xlsx and .csv are fine),"
    " must contain 'living_area' (float), 'outer_territory' (str) and 'inner_territory' (str) columns",
    required=True,
)
@click.option(
    "--territories_output",
    "-oi",
    type=click.Path(dir_okay=False),
    help="Filename for a balanced inner territories export (.json, .xlsx and .csv formats are supported)",
    default="output/territories.json",
    show_default=True,
)
@click.option(
    "--houses_output",
    "-oh",
    type=click.Path(dir_okay=False),
    help="Filename for a populated buildings export (.json, .geojson, .xlsx and .csv formats are supported)",
    default="output/houses.json",
    show_default=True,
)
@click.option(
    "--verbose", "-v", 
    is_flag=True, 
    help="Increase logger verbosity to DEBUG and print some additional statements"
)
def balance(
    total_population: int,
    territories: str,
    houses: str,
    territories_output: str,
    houses_output: str,
    verbose: bool = False
) -> None:
    """Balance dwellings total population

    Balance population for the given city provided with total population (accurate value), populations of inner and
    outer territory units (optional), list of buildings with living area value, and probability values of a person
    sex, age and social group.
    """

    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")
    try:
        territories_df = read_file(territories)
        houses_df = read_file(houses)
    except Exception as exc:  # pylint: disable=broad-except
        logger.critical("Exception on reading input data: {!r}", exc)
        if verbose:
            traceback.print_exc()
        sys.exit(1)

    territories_df, houses_df = pbalance(total_population, 
                                         territories_df, 
                                         houses_df, 
                                         verbose)

    logger.opt(colors=True).info("Saving to file <cyan>{}</cyan>", territories_output)
    to_file(territories_df, territories_output)
    logger.opt(colors=True).info("Saving to file <cyan>{}</cyan>", houses_output)
    to_file(houses_df, houses_output)
