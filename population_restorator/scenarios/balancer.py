"""Balance command-line utility configuration is defined here."""
from __future__ import annotations

import sys
import traceback

import pandas as pd
from loguru import logger

from population_restorator.balancer import balance_houses, balance_territories
from population_restorator.utils.data_saver import to_file
from population_restorator.utils.data_structure import city_as_territory

def balance(  # pylint: disable=too-many-arguments,too-many-locals
    total_population: int,
    territories_df: pd.DataFrame,
    houses_df: pd.DataFrame,
    main_territory: pd.DataFrame | None = None,
    verbose: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Balance dwellings total population

    Balance population for the given city provided with total population (accurate value), populations of inner and
    outer territory units (optional), list of buildings with living area value, and probability values of a person
    sex, age and social group.
    """

    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    try:
        city = city_as_territory(total_population, territories_df, houses_df, main_territory)
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

    territories_new_df = pd.DataFrame(
        (
            # all inner territories representaning
            [
                {
	                "name": territory.name,
	                "population": territory.population,
	                "inner_territories_population": territory.get_total_territories_population(),
	                "houses_number": territory.get_all_houses().shape[0],
	                "houses_population": territory.get_total_houses_population(),
	                "total_living_area": territory.get_total_living_area(),  # tobefixed floatin .00000000000001
	            }
	            for territory in city.inner_territories
	        ]
	         + 
            # self city representating
            [
	            {
	                "name": city.name,
	                "population": city.population,
	                "inner_territories_population": city.get_total_territories_population(),
	                "houses_number": city.get_all_houses().shape[0],
	                "houses_population": city.get_total_houses_population(),
	                "total_living_area": city.get_total_living_area(),
	            }
	        ]
	    )
    )
    return (territories_new_df, city.get_all_houses())
