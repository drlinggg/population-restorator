from sqlalchemy import Table, Column, Integer, ForeignKey

from population_restorator.db import metadata

t_population_divided = Table(
    "population_divided",
    metadata,
    Column("year", Integer, primary_key=True, nullable=False),
    Column("house_id", Integer, ForeignKey("houses_tmp.id"), primary_key=True, nullable=False),
    Column("territory_id", Integer, primary_key=True, nullable=False),
    Column("age", Integer, primary_key=True, nullable=False),
    Column("social_group_id", Integer, ForeignKey("social_groups_probabilities.id"), primary_key=True, nullable=False),
    Column("men", Integer, nullable=False),
    Column("women", Integer, nullable=False),
)
"""Final population division.
Columns:
- year - year of division, integer
- house_id - house identifier, integer
- territory_id - territory identifier, integer
- age - age of a person, integer
- social_group_id - social group identifier, integer
- men - number of men with the given age and social group in the given house at the given year, integer
- women - number of women with the given age and social group in the given house at the given year, integer"""
