"""Data structure transformation methods are defined here."""
import pandas as pd
from loguru import logger
from numpy import nan

from population_restorator.models import Territory


def _check_intergrity(outer_territories: pd.DataFrame, inner_territories: pd.DataFrame, houses: pd.DataFrame) -> None:
    if "name" not in outer_territories.columns:
        raise ValueError("'name' column is missing in outer_territories")
    if "name" not in inner_territories.columns:
        raise ValueError("'name' column is missing in inner_territories")
    if "outer_territory" not in inner_territories.columns:
        raise ValueError("'outer_territory' column is missing in inner_territories")
    if "inner_territory" not in houses.columns:
        raise ValueError("'inner_territory' column is missing in houses")
    if "living_area" not in houses.columns:
        raise ValueError("'living_area' column is missing in houses")
    if (good_houses_count := len(houses["living_area"] >= 0)) != houses.shape[0]:
        raise ValueError(
            "some houses have 'living_area' value invalid or < 0 -"
            f" totally {houses.shape[0] - good_houses_count} entries"
        )
    logger.debug("Data integrity check passed")


def city_as_territory(
    total_population: int, outer_territories: pd.DataFrame, inner_territories: pd.DataFrame, houses: pd.DataFrame
) -> Territory:
    """Represent city with two layers of territory division as a single territory.

    Args:
        total_population (int): total city population
        outer_territories (DataFrame): pandas DataFrame of outer city territories, must contain 'name' (str)
        and optionally 'population' columns
        inner_territories (DataFrame): pandas DataFrame of inner city territories, must contain 'name' (str),
        'outer_territory' and optionally 'population' columns. Each 'outer_territory' column value must be present in
        `outer_territories`.
        houses (DataFrame): houses dataframe, must contain 'living_area' (float) and 'inner_territory' (str) columns.
        Each 'inner_territory' column value must be present in `inner_territories`.

    Returns:
        Territory: territory named 'city' containing all of the outer territories, each of them containing corresponding
        inner territories, each of them containing corresponding buildings.
    """
    _check_intergrity(outer_territories, inner_territories, houses)
    logger.debug("Returning city as territory")
    return Territory(
        "city",
        total_population,
        [
            Territory(
                ot["name"],
                ot["population"] if "population" in ot else None,
                [
                    Territory(
                        it["name"],
                        it["population"] if "population" in it else None,
                        houses=houses[houses["inner_territory"] == it["name"]].copy().reset_index(drop=True),
                    )
                    for _, it in inner_territories[inner_territories["outer_territory"] == ot["name"]]
                    .replace({nan: None})
                    .iterrows()
                ],
            )
            for _, ot in outer_territories.replace({nan: None}).iterrows()
        ],
    )
