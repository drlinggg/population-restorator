"""Main group for subcommands registration."""
import click


@click.group()
def main():
    """Population restorator command-line utility.

    With three steps you can get the level of houses population information that suits your purposes:

    1. Model total dwellings population based on total city (and inner/outer territory units if
    information is available) population

    2. Based on total dwellings population divide people by age, sex and social group using probability distribution
    information provided.

    3. Propagade population change on the given period based on the proided information.
    """
