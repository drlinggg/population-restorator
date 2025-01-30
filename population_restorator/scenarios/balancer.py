"""Balance command-line utility configuration is defined here."""
from __future__ import annotations

import itertools
import sys
import traceback

import pandas as pd
from loguru import logger

from population_restorator.balancer import balance_houses, balance_territories
from population_restorator.utils import read_file
from population_restorator.utils.data_saver import to_file
from population_restorator.utils.data_structure import city_as_territory

def balance(  # pylint: disable=too-many-arguments,too-many-locals
    total_population: int,
    territories_df: pd.DataFrame,
    houses_df: pd.DataFrame,
    verbose: bool = False,
    territories_output: str = 'output/territories',
    houses_output: str = 'output/houses',
) -> None:
    """Balance dwellings total population

    Balance population for the given city provided with total population (accurate value), populations of inner and
    outer territory units (optional), list of buildings with living area value, and probability values of a person
    sex, age and social group.
    """

    print('test')

    if territories_output is not None:
        if territories_output.lower().endswith(".geojson"):
            logger.error("Unable to export balanced inner territories as geojson, use .csv, .xlsx or .json instead")
            sys.exit(1)

    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")
    try:
        city = city_as_territory(total_population, territories_df, houses_df)
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
