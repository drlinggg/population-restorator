"""This module is used to divide houses population on sex, age and social groups."""
from __future__ import annotations

import time

import numpy as np
from loguru import logger

from population_restorator.models import SocialGroupsDistribution


def divide_houses(  # pylint: disable=too-many-locals
    houses_population: list[int],
    social_groups: SocialGroupsDistribution,
    rng: np.random.Generator | None = None,
) -> list[np.ndarray]:
    """Divide houses population by sex, age and social groups.

    Args:
        houses (list[int]): houses, must have population located in `population` column.
        social_groups (SocialGroupsDistribution): People distribution by social_group, sex and age for non-crossings
        and additonal social groups.
        rng (numpy.random.Generator, optional): optional random generator.

    Returns:
        list[ndarray]: people distribution for houses in format of numpy array with shape [<social_groups>, 2, <ages>].
        First dimension is a social group (index = index in `social_groups.get_combined_names()`), second - sex
        (0 - man, 1 - woman) and third is age (index = age).
    """
    sgs = social_groups.primary_as_probability_array()  # [sgs, 2, ages]
    sgs_prob = sgs.flatten()  # [sgs * 2 * ages]
    sgs_a = social_groups.additonals_as_probability_array()  # [2, ages, sgs_a]
    sg_names = social_groups.get_combined_names()
    single_house_population = np.array([0] * (len(sg_names) * sgs.shape[1] * sgs.shape[2])).reshape(
        [len(sg_names), sgs.shape[1], sgs.shape[2]]
    )  # [(sgs + sgs_a), 2, ages]

    divided_population = []

    if rng is None:
        rng = np.random.default_rng(seed=int(time.time()))

    sgs_range = list(range(sgs_prob.shape[0]))
    for house_number, population in enumerate(houses_population):
        if population == 0:
            divided_population.append(single_house_population.copy())
            continue
        change_values = np.unique(
            rng.choice(sgs_range, population, replace=True, p=sgs_prob),
            return_counts=True,
        )
        div_pop = single_house_population.flatten()
        house_pop = []
        for idx, cnt in zip(change_values[0], change_values[1]):
            div_pop[idx] = cnt
            house_pop.extend([idx] * cnt)

        div_pop = div_pop.reshape(single_house_population.shape)

        sgs_a_range = list(range(sgs.shape[0], sgs.shape[0] + sgs_a.shape[2]))
        additional_population = population * social_groups.get_additional_probability()
        for _ in range(int(additional_population)):
            for _tries in range(20):
                person_idx = rng.choice(house_pop)
                sg_idx = person_idx // (sgs.shape[1] * sgs.shape[2])
                sex_idx = (person_idx - sg_idx * sgs.shape[1] * sgs.shape[2]) // sgs.shape[2]
                age = person_idx - sg_idx * sgs.shape[1] * sgs.shape[2] - sex_idx * sgs.shape[2]

                if sgs_a[sex_idx, age].sum() == 1:
                    break
            else:
                logger.error(
                    "Could not divide population of a house numebr {} ({} population)", house_number, population
                )
                break

            additional_sg_idx = rng.choice(sgs_a_range, p=sgs_a[sex_idx, age])
            div_pop[additional_sg_idx, sex_idx, age] += 1
        divided_population.append(div_pop.copy())

    return divided_population
