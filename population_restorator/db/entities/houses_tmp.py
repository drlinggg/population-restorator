"""Houses table schema is defined here."""
from sqlalchemy import Column, Float, Integer, Table

from population_restorator.db import metadata


t_houses_tmp = Table(
    "houses_tmp",
    metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("capacity", Float, nullable=False),
)
"""Houses with capacity (abstract number based on living area or people setteled).

Columns:
- `id` - house identifier, integer
- `capacity` - house capacity to compare with others, float
"""
