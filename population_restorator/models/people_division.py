"""PeopleDivision class holding a people division for a concrete social group is defined here."""
from dataclasses import dataclass


@dataclass
class PeopleDivision:
    """An absolute number division of people of a given social group by sex and age."""

    men: list[int]
    women: list[int]

    def __post_init__(self) -> None:
        if len(self.men) != len(self.women):
            raise ValueError(
                f"Length of men ({len(self.men)}) and women ({len(self.women)}) distribution lists must be equal"
            )
