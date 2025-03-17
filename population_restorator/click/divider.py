"""Balance command-line utility configuration is defined here."""
from __future__ import annotations

import datetime
import sys
import traceback

import click
from loguru import logger

from population_restorator.models.parse.social_groups import parse_distribution
from population_restorator.utils import read_file
from population_restorator.utils.data_saver import to_file
from population_restorator.scenarios import divide as pdivide

from .main_group import main


@main.command("divide")
@click.option(
    "--houses",
    "-h",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the social groups json file with 'social_groups' attribute, each object having 'ages_men' and"
    " 'ages_women' lists",
    required=True,
)
@click.option(
    "--social_groups",
    "-s",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the social groups json file with 'social_groups' attribute, each object having 'ages' list",
    required=True,
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False),
    help="Filename for a SQLite database file to store buildings with people divided by age, sex and social group",
    default="houses_divided.sqlite",
    show_default=True,
)
@click.option(
    "--output_ids",
    "-oi",
    type=click.Path(dir_okay=False),
    help="Filename for a copy of input houses file with 'id' attribute added (created only if it was missing)",
    default=None,
    show_default="<input_houses>_with_ids.csv",
)
@click.option(
    "--year",
    "-y",
    type=int,
    help="Year to save database as",
    default=None,
    show_default="<current year>",
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Increase logger verbosity to DEBUG and print some additional stataments"
)
def divide(  # pylint: disable=too-many-arguments,too-many-locals
    houses: str,
    social_groups: str,
    output: str,
    output_ids: str | None,
    year: int | None,
    verbose: bool,
) -> None:
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

    try:
        houses_df = read_file(houses)
    except Exception as exc:  # pylint: disable=broad-except
        logger.critical("Exception on reading input data: {!r}", exc)
        if verbose:
            traceback.print_exc()
        sys.exit(1)

    id_added = "id" not in houses_df.columns
    if id_added:
        houses_df["id"] = range(houses_df.shape[0])
        if output_ids is None:
            output_ids = f"{houses[:houses.rindex('.')]}_with_ids.csv"
        logger.warning(f"Adding identifier column 'id' and saving file with ids to {output_ids}")
        to_file(houses_df.set_index("id"), output_ids)

    houses_df = houses_df.set_index("id")

    logger.info("Parsing sex-age-social_groups distribution from file {}", social_groups)
    distribution = parse_distribution(social_groups)

    houses_df, distribution_series = pdivide(houses_df, distribution, year, verbose)

    logger.info("Saving results to {}", output)

    to_file(houses_df, "output/divider/test1.json")
    distribution_series.to_csv("output/divider/test2.csv")
