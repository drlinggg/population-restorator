"""Social groups distribution model is defined here."""
from dataclasses import dataclass
from typing import Callable

import numpy as np

from .people_division import PeopleDivision
from .sex_age import SexAgeDistribution


@dataclass
class SocialGroupWithProbability:
    """Probability for a person to be in a given social group and propbability distribution for a person of a
    given social group to be given sex an age.
    """

    name: str
    probability: float
    distribution: SexAgeDistribution

    @classmethod
    def from_values(  # pylint: disable=too-many-arguments
        cls,
        name: str,
        probability: float,
        men: list[float],
        women: list[float],
    ):
        """Construct SocialGroup from its name, probability and `SexAgeDistribution` aruments

        Args:
            name (str): social group name.
            probability (float): probatility for a person to be in this social group.
            men (list[float]): list of number men divided by age or list of probabilities for a man in this
            social group to be a given age.
            women (list[float]): list of number women divided by age or list of probabilities for a woman in
            this social group to be a given age.
        """
        return cls(name, probability, SexAgeDistribution(men, women))


@dataclass
class SocialGroupsDistribution:
    """List of primary (meaning that a person could only be one of them) and additional (meaning that a person of a
    non-crossing social group can be also a member of one of the additional social groups) social groups together.
    """

    primary: list[SocialGroupWithProbability]
    additional: list[SocialGroupWithProbability]

    def primary_as_probability_array(self) -> np.ndarray:
        """Represent non-crossing social groups distribution as a single numpy array with shape
        [<social_groups>, 2, <ages>]. Sum of the array equals to 1.0.

        First dimension is social_group (index = index in `self.primary`), second - sex (0 - man, 1 - woman),
        third - age (index = age).
        """
        sgs = np.array([sg.distribution.as_probability_array() * sg.probability for sg in self.primary])
        total_value = sgs.sum()
        return sgs / total_value

    def additonals_as_probability_array(self) -> np.ndarray:
        """Represent additional social groups distribution as a single numpy array with shape
        [2, <ages>, <social_groups>]. Sum of the each line of third dimentsion equals to 1.0.

        First dimension is sex (0 - man, 1 - woman), second - age (index = age), third - social group (index = index
        in `self.additionals`)
        """
        sgs = np.array([sg.distribution.as_probability_array() * sg.probability for sg in self.additional])
        return np.array(
            [
                np.array(
                    [
                        (  # pylint: disable=unnecessary-direct-lambda-call
                            lambda arr: arr / arr.sum() if arr.sum() != 0 else arr
                        )(sgs[:, sex_range, age_range])
                        for age_range in range(sgs.shape[2])
                    ]
                )
                for sex_range in range(sgs.shape[1])
            ]
        )

    def get_combined_names(self) -> list[str]:
        """Get a single list of primary and additional social groups names without changing the order."""
        return [sg.name for sg in self.primary] + [sg.name for sg in self.additional]

    def get_additional_probability(self) -> float:
        """Get a summary probability for a person to be a part of any additional social group"""
        return sum(sg.probability for sg in self.additional)

    def get_resulting_function(self) -> Callable[[np.ndarray], dict[str, PeopleDivision]]:
        """Get a function which will return a dictionary of social_group -> PeopleDistribution based on a given
        house numpy array of a shape [`social_gropus_promary` + `social_groups_additional`, 2, `ages`]
        """

        def inner_func(distribution: np.ndarray) -> dict[str, PeopleDivision]:
            """Get people distribution based on the given people array divided by social groups and ages."""
            return {
                sg_name: PeopleDivision(sg[0].tolist(), sg[1].tolist())
                for sg, sg_name in zip(distribution, self.get_combined_names())
            }

        return inner_func
