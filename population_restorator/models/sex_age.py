"""Sex-age distribution model is located here."""
from dataclasses import dataclass

import numpy as np


@dataclass
class SexAgeDistribution:
    """Sex-age distribution model. It shows the probability of a person to be man or woman, and then depending on the
    sex, to have the age in range of length of `men`/`women` list length.

    After construction (men_total + women_total) == sum(self.men) == sum(self.women) == 1.0
    """

    men: list[float]
    women: list[float]

    def __post_init__(
        self,
    ):
        """Check `SexAgeDistribution` initialization.

        Raises:
            ValueError: in case len(men) != len(women), if any of lists is empty, men_total + women_total == 0 or sum of
            any of lists elements is 0.
        """
        if len(self.men) != len(self.women) or len(self.men) == 0:
            raise ValueError(
                f"Length of men age distribution ({len(self.men)}) differs from the length of"
                f" women age distribution ({len(self.women)})"
            )
        if sum(self.men) + sum(self.women) == 0:
            raise ValueError("Probabilities/number of men list and women list must not sum to zero")
        if (men_sum := sum(self.men)) + (women_sum := sum(self.women)) != 1.0:
            self.men = [m / (men_sum + women_sum) for m in self.men]
            self.women = [w / (men_sum + women_sum) for w in self.women]

    def as_probability_array(self) -> np.ndarray:
        """Represent sex-age distribution as numpy array with shape [2, <ages>]. Sum of the array equals to 1.0.

        First dimension is sex (0 - man, 1 - woman) and second is for age (index = age).
        """
        men = np.array(self.men)
        women = np.array(self.women)
        total = men.sum() + women.sum()
        return np.array([men / total, women / total])
