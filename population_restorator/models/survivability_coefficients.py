"""Survivability coefficients class is defined here."""
from dataclasses import dataclass


@dataclass
class SurvivabilityCoefficients:
    """Survivability coefficients for (N) ages: `men` and `women` lists of floats containing (N - 1) elements.

    Coefficients can be larger than 1.0 which means that the given age death are lower than incoming migration.
    """

    men: list[float]
    women: list[float]

    def __post_init__(self) -> None:
        """Check that length of men and women is the same."""
        if len(self.men) != len(self.women):
            raise ValueError(
                f"Length of men ({len(self.men)}) and women ({len(self.women)}) survivability coefficients"
                " must be the same"
            )
