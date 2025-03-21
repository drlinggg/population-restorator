"""City balancing method is defined here."""
from __future__ import annotations

import time

import numpy as np
from loguru import logger

from population_restorator.models import Territory


def balance_territories(territory: Territory, rng: np.random.Generator | None = None) -> None:
    """Balance territories population without balancing houses. 
    The process is performed for all depth levels from top to bottom.

    `rng` is an optional random generator from numpy.
    """

    if len(territory.inner_territories) == 0:
        return

    if rng is None:
        rng = np.random.default_rng(seed=int(time.time()))

    for inner_territory in territory.inner_territories:
        if inner_territory.population is None:
            logger.trace("Territory '{}' inner territory '{}' have None population, setting to 0")
            inner_territory.population = 0

    if (current_population := sum(it.population for it in territory.inner_territories)) < territory.population:
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

        if (total_living_area != 0.0):
            distribution = [area / total_living_area for area in distribution]
        else:
            distribution = [1.0 / len(territory.inner_territories) for area in distribution]

        change_values = np.unique(
            rng.choice(list(range(len(territory.inner_territories))),
                abs(compensation),
                replace=True,
                p=distribution),
            return_counts=True,
        )

        for idx, change in zip(change_values[0], change_values[1]):
            if territory.inner_territories[idx].population + int(change * sign) < 0:
                logger.error(
                    "While compensating {} people, territory {} got compensation {} and now its negative",
                    compensation,
                    territory.inner_territories[idx].name,
                    int(change * sign),
                )
            territory.inner_territories[idx].population += int(change * sign)

    elif (current_population := sum(it.population for it in territory.inner_territories)) > territory.population:
        compensation = territory.population - current_population

        """
        There were a problem if parent node had less population than his childs. I suppose
        the best way to handle it is to send a warning 
        that above node has less than it needs to give and believe lower nodes
        """
        logger.warning(
            "Ignored compensation because {} is more than {} territory population {},",
            compensation,
            territory.name,
            territory.population
        )

    else:
        logger.trace("Territory {} is balanced well", territory.name)

    for inner_territory in territory.inner_territories:
        balance_territories(inner_territory)

    territory.population = sum(it.population for it in territory.inner_territories)
