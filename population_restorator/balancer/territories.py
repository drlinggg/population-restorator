"""City balancing method is defined here."""
from __future__ import annotations

import time

import numpy as np
from loguru import logger

from population_restorator.models import Territory


def balance_territories(territory: Territory, rng: np.random.Generator | None = None) -> None:
    """Balance territories population without balancing houses. The process is performed for all depth levels
    from top to bottom.

    `rng` is an optional random generator from numpy.
    """
    if territory.inner_territories is None:
        return

    if rng is None:
        rng = np.random.default_rng(seed=int(time.time()))

    for inner_territory in territory.inner_territories:
        if inner_territory.population is None:
            logger.trace("Territory '{}' inner territory '{}' have None population, setting to 0")
            inner_territory.population = 0

    if (current_population := sum(it.population for it in territory.inner_territories)) != territory.population:
        compensation = territory.population - current_population
        logger.debug(
            "Compensating {} people for territory '{}' inner territories (needed population is {})",
            compensation,
            territory.name,
            territory.population,
        )
        sign = 1 if compensation > 0 else -1
        distribution = [it.get_total_living_area() for it in territory.inner_territories]
        total_living_area = sum(distribution)
        distribution = [area / total_living_area for area in distribution]
        change_values = np.unique(
            rng.choice(list(range(len(territory.inner_territories))), abs(compensation), replace=True, p=distribution),
            return_counts=True,
        )
        for idx, change in zip(change_values[0], change_values[1]):
            territory.inner_territories[idx].population += int(change * sign)
    else:
        logger.trace("Territory {} is balanced well", territory.name)

    for inner_territory in territory.inner_territories:
        balance_territories(inner_territory)
