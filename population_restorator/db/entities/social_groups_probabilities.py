"""Social groups table schema is defined here."""
from sqlalchemy import Boolean, Column, Float, Integer, String, Table

from population_restorator.db import metadata


t_social_groups_probabilities = Table(
    "social_groups_probabilities",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(150), nullable=False),
    Column("probability", Float, nullable=False),
    Column("is_primary", Boolean, nullable=False),
)
"""Social groups with probabilities.

Columns:
- `id` - social group identifier, integer
- `name` - social group name, varchar(150)
- `probability` - probability for a person to be in a given social group, float
- `is_primary` - indicates whether the social group is primary or additional for a person, boolean
"""
