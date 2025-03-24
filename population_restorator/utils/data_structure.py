"""Data structure transformation methods are defined here."""
from __future__ import annotations

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
    if "territory_id" not in houses.columns:
        raise ValueError("'territory_id' column is missing in houses")
    if (good_houses_count := len(houses["living_area"] >= 0)) != houses.shape[0]:
        raise ValueError(
            "some houses have 'living_area' value invalid or < 0 -"
            f" totally {houses.shape[0] - good_houses_count} entries"
        )

    houses["living_area"] = houses["living_area"].fillna(0)
    territories["population"] = territories["population"].fillna(0)

    logger.debug("Data integrity check passed")


def city_as_territory(
    total_population: int,
    internal_territories_df: pd.DataFrame,
    internal_houses_df: pd.DataFrame,
    main_territory: pd.DataFrame | None = None
) -> Territory:

    """Represent city with two layers of territory division as a single territory.
    Args:
        total_population (int): total city population
        internal_territories_df (DataFrame) : territories dataframe of inner territories of city (tree-like presentable)
        internal_houses_df (DataFrame): houses dataframe, must contain 'living_area' (float) and 'territory_id' (int) columns.
    Returns:
        ...
    """

    _check_intergrity(internal_territories_df, internal_houses_df)
    internal_territories_df.sort_values("parent_id", inplace=True)
    internal_houses_df.sort_values("territory_id", inplace=True)

    if (main_territory is None):
        logger.warning("main territory is None, trying to resolve...")
        main_territory_id = internal_territories_df.iloc[0]['parent_id'] if len(internal_territories_df) else None
        main_territory_parent_id = None,
        main_territory_name = None,
    else:
        main_territory_id = main_territory.iloc[0]["territory_id"]
        main_territory_parent_id = main_territory.iloc[0]["parent_id"]
        main_territory_name = main_territory.iloc[0]["name"]


    logger.debug("Returning city as territory")
    city = Territory(
            population=total_population,
            territory_id=main_territory_id,
            parent_id=main_territory_parent_id,
            name=main_territory_name,
            inner_territories=[],
            houses=pd.DataFrame(columns=["territory_id", "population", "living_area", "geometry"])
    )

    if len(internal_territories_df) == 0:
        logger.warning("Territory has no inner territories")
        return city

    print(city)
    print(internal_territories_df)

    """This creating territory tree method is working when all territory_id > parent_id for each territory"""
    territories: list["Territory"] = []
    cur_parent = internal_territories_df.iloc[0]['parent_id']

    for i in range(len(internal_territories_df)):
        if (cur_parent != internal_territories_df.iloc[i]['parent_id']):
            territory = city.find_inner_territory_by_id(cur_parent)
            territory.inner_territories = territories
            territories = []
            cur_parent = internal_territories_df.iloc[i]['parent_id']

        territories.append(
            Territory(
                internal_territories_df.iloc[i]['population'],
                internal_territories_df.iloc[i]['territory_id'],
                internal_territories_df.iloc[i]['parent_id'],
                internal_territories_df.iloc[i]['name'],
            )
        )

    territory = city.find_inner_territory_by_id(cur_parent)
    territory.inner_territories = territories

    """Adding to each territory its houses"""
    for i in range(len(internal_territories_df)):
        territory = city.find_inner_territory_by_id(internal_territories_df.iloc[i]['territory_id'])
        territory.houses = internal_houses_df.query(f'territory_id == {territory.territory_id}')

    return city
