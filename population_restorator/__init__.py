"""Population balancer package.

It can be used to balance city houses population in 3 steps:
- settle people to dwellings useing total city population and houses living area
- divide people in houses to ages and social groups using number of people and variances values to
- forecast the people number over the following years depending on scenario
"""
from population_restorator import balancer, divider, forecaster, models


__version__ = "0.2.0"
