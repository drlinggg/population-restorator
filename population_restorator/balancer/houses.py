"""City houses balancing method is defined here."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from loguru import logger

from population_restorator.models import Territory


def balance_houses(territory: Territory, rng: np.random.Generator | None = None) -> None:
    """Balance territories population without balancing houses. The process is performed for all depth levels
    from top to bottom.

    `rng` is an optional random generator from numpy.
    """
    if territory.inner_territories is not None:
        for inner_territory in territory.inner_territories:
            balance_houses(inner_territory)
        return

    if rng is None:
        rng = np.random.default_rng(seed=int(time.time()))

    living_area = territory.get_total_living_area()
    if living_area < 5:
        logger.warning(
            "Houses ({:3}) have no living area, skipping requested {:6} people population for territory '{}' ",
            territory.houses.shape[0],
            territory.population,
            territory.name,
        )
        territory.houses["population"] = None
        return

    logger.debug(
        "Performing buildings population balancing ({:3} houses, total living area = {:9.1f}"
        " for population of {:6}) for territory '{}'",
        territory.houses.shape[0],
        living_area,
        territory.population,
        territory.name,
    )

    if "population" in territory.houses.columns:
        territory.houses["population"] = territory.houses["population"].fillna(0)
        try:
            current_population = int(territory.houses["population"].sum())
        except Exception as exc:
            logger.error(
                "Territory '{}' houses have something wrong with population data - could not perform balancing: {!r}",
                territory.name,
                exc,
            )
            raise ValueError(f"Something is wrong with initial territory '{territory.name}' data") from exc
    else:
        territory.houses["population"] = pd.Series([0] * territory.houses.shape[0], dtype=int)
        current_population = 0

    compensation = territory.population - current_population
    logger.trace(
        "Compensating {} people for territory '{}' houses (needed population is {})",
        compensation,
        territory.name,
        territory.population,
    )
    sign = 1 if compensation > 0 else -1
    distribution = list(territory.houses["living_area"])
    total_living_area = sum(distribution)
    distribution = [area / total_living_area for area in distribution]
    change_values = np.unique(
        rng.choice(list(range(territory.houses.shape[0])), abs(compensation), replace=True, p=distribution),
        return_counts=True,
    )
    houses_population = list(territory.houses["population"])
    for idx, change in zip(change_values[0], change_values[1]):
        houses_population[idx] += change * sign

    territory.houses["population"] = houses_population
