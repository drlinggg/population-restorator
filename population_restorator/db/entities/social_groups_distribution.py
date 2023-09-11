"""Social groups distribution table schema is defined here."""
from sqlalchemy import Column, Float, ForeignKey, Integer, Table

from population_restorator.db import metadata


t_social_groups_distribution = Table(
    "social_groups_distribution",
    metadata,
    Column("social_group_id", Integer, ForeignKey("social_groups_probabilities.id"), primary_key=True, nullable=False),
    Column("age", Integer, primary_key=True, nullable=False),
    Column("men_probability", Float, nullable=False),
    Column("women_probability", Float, nullable=False),
    Column("men_sg", Float, nullable=False, default=0),
    Column("women_sg", Float, nullable=False, default=0),
)
"""Sex-age distribution statistics inside social groups.

Columns:
- `social_group_id` - social group identifier, integer
- `age` - age of a person, integer
- `men_probability` -   probatility for a person of a social group to be a man   of the given age, float
- `women_probability` - probatility for a person of a social group to be a woman of the given age, float
- `men_probability` -   probatility for a men   of a given age to have a given social_group, float
- `women_probability` - probatility for a women of a given age to have a given social_group, float
"""
