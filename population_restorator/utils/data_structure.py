"""Data structure transformation methods are defined here."""
import pandas as pd
from loguru import logger
from numpy import nan

from population_restorator.models import Territory


def _check_intergrity(territories: pd.DataFrame, houses: pd.DataFrame) -> None:
    if "name" not in territories.columns:
        raise ValueError("'name' column is missing in territories")
    if "parent_id" not in territories.columns:
        raise ValueError("'parent_id' column is missing in territories")
    if "living_area" not in houses.columns:
        raise ValueError("'living_area' column is missing in houses")
    if (good_houses_count := len(houses["living_area"] >= 0)) != houses.shape[0]:
        raise ValueError(
            "some houses have 'living_area' value invalid or < 0 -"
            f" totally {houses.shape[0] - good_houses_count} entries"
        )
    logger.debug("Data integrity check passed")


def city_as_territory(
    total_population: int, internal_territories_df: pd.DataFrame, houses: pd.DataFrame
) -> Territory:

    #todo desc

    """Represent city with two layers of territory division as a single territory.

    Args:
        ...
        houses (DataFrame): houses dataframe, must contain 'living_area' (float) and 'inner_territory' (str) columns.
        Each 'inner_territory' column value must be present in `inner_territories`.

    Returns:
        ...
    """

    _check_intergrity(internal_territories_df, houses)
    logger.debug("Returning city as territory")

    city = Territory("Бибирево", total_population, internal_territories_df.iloc[0]['parent_id'], None)

    territories: list["Territory"] = list()
    cur_parent = internal_territories_df.iloc[0]['parent_id']

    for i in range(len(internal_territories_df)):
        if (cur_parent != internal_territories_df.iloc[i]['parent_id']):
            territory = city.find_inner_territory_by_id(cur_parent)
            if not(territory.inner_territories):
                territory.inner_territories = list()
            territory.inner_territories = territories
            territories = []
            cur_parent = internal_territories_df.iloc[i]['parent_id']
                
        territories.append(
            Territory(
                internal_territories_df.iloc[i]['name'],
                internal_territories_df.iloc[i]['population'],
                internal_territories_df.iloc[i]['territory_id'],
                internal_territories_df.iloc[i]['parent_id'],
            )
        )
        
    territory = city.find_inner_territory_by_id(cur_parent)
    territory.inner_territories = territories

    # do stuff with houses

    return city

