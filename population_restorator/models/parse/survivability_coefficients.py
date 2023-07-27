"""Survivability coefficients parsing method is defined here."""

import json

from population_restorator.models.survivability_coefficients import SurvivabilityCoefficients


def read_coefficients(path: str) -> SurvivabilityCoefficients:
    """Read survivability coefficients from the given file."""
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return SurvivabilityCoefficients(data["men"], data["women"])
