"""Balance command-line utility configuration is defined here."""
from __future__ import annotations

import itertools
import sys
import traceback

import click
import pandas as pd
from loguru import logger

from population_restorator.utils import read_file
from population_restorator.utils.data_saver import to_file

from population_restorator.scenarios import balance

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
    "--territories_output",
    "-oi",
    type=click.UNPROCESSED,
    metavar="Path",
    help="Filename for a balanced inner territories export (.json, .xlsx and .csv formats are supported)",
    default=None,
    show_default=True,
)
@click.option(
    "--houses_output",
    "-oh",
    type=click.Path(dir_okay=False),
    help="Filename for a populated buildings export (.json, .geojson, .xlsx and .csv formats are supported)",
    default="houses_balanced.csv",
    show_default=True,
)
def balance(  # pylint: disable=too-many-arguments,too-many-locals
    total_population: int,
    territories: str,
    houses: str,
    verbose: bool = False,
    territories_output: str, #tobechanged
    houses_output: str,
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

    #handle None output path
    balance(total_population, territories, houses, verbose, territories_output, houses_output)

