# population_restorator

This utility can be used to balance city houses population in 3 steps:
- settle people to dwellings useing total city population and houses living area
- divide people in houses to ages and social groups using number of people and variances values to
- forecast the people number over the following years depending on scenario

## Installing

Install with `make install` (`pipx install .`) after cloning repository manually or directly from github `pipx install git+https://kanootoko/population_restorator`

## Running

Run with `population-restore --help`

## Develpment

1. Install poetry and prepare environment (`pipx install poetry`; `poetry install --with dev`; `poetry shell`)
2. Initialize pre-commit by running `pre-commit install`
3. Make changes to the code in a separate branch or repository (`git checkout -b <branch-name>`)
4. Before commit, run `make format lint` to auto-format your code and check it with pylint
5. Commit your changes
6. Create pull-request to _dev_ branch

## Usage example

### Input data

Sample data is given in the [sample data directory](sample_data). You can prepare your own input following its format.

In IDU lab at ITMO University you can get export Postgres database information using pg_save utility for example.
For a city with id=1 one can use following commands (implying database access settings are set elsewhere):

```bash
pg-save query -o input/houses.geojson "SELECT building_id as id, living_area, municipality as inner_territory, geometry FROM all_buildings where is_living = true and living_area > 0 and city_id = 1"
pg-save query -o input/outer_territories.geojson "SELECT id, name, population, geometry FROM administrative_units WHERE city_id = 1"
pg-save query -o input/inner_territories.geojson "SELECT id, name, population, (SELECT name FROM administrative_units WHERE id = admin_unit_parent_id) as outer_territory, geometry FROM municipalities WHERE city_id = 1"
pg-save query "SELECT population FROM cities WHERE id = 1"
```

### Balancing people to dwellings

To get the buildings populations you will need following input data:
- total city population - required. This is a base number which will be splitted to the houses
- outer city territories - required. Optional population attribute
- inner city territories - required. Mandatory `outer_territory` and optional population attributes
- houses - required. Mandatory `inner_territory` and `living_area` attributes and optional `population` to start with

As the output you will get the same buildings, but having `population` attribute filled. Sum of its value for all of the buildings
  will be equal to the given total city population (the only exception is when inner/outer territories have population set, but no real houses are present inside).

You can also save inner and outer territories with balanced population as well.

#### Launch example:

```bash
python -m zipfile -e sample_data/balancer/balancer.zip sample_data/balancer
population-restore balance -dp 372000 -di sample_data/balancer/inner_territories.geojson -do sample_data/balancer/outer_territories.geojson -dh sample_data/balancer/houses.geojson -o output/houses_balanced.geojson -oi output/inner_territories_balanced.csv -oo output/outer_territories_balanced.csv
```

where:
- -dp - total city population
- -di - input inner territories information file
- -do - input outer territories information file
- -dh - input houses information file
- -o  - output file for houses with balanced population
- -oi - output file for balanced inner territories
- -oo - output file for balanced outer territories

Note that outer territories summary population is 370624, not 327000, so 1376 will be added to outer territories first and inner territories after that.

All files may have geojson, json, csv or xlsx format

### Dividing balanced people in dwellings by sex, age and social groups

After the houses are populated with abstract people, you can concretize its composition.

To do so you will need following input data:
- houses - required. Mandatory `population` and optional `id` attributes.
- social groups file - required.

    This is a json file with the only entry "social_groups" - a list of objects with attributes:
    - `name` - string
    - `ages_men` - list of integers/floats (absolute number of people or probability distribution which sums up to 1.0)
    - `ages_women` - list of integers/floats (absolute number of people or probability distribution which sums up to 1.0)
    - `total` - total number of social group representatives (for the case when ages_men and ages_women are given as a probability distribution)
      (optional, default `sum(ages_men) + sum(ages_women)` if its values are absolute)
    - `is_additional` - boolean (optional, default - false)

    Alternatively (as a third option) `ages_men` and `ages_women` can be set as integers to represent total number of men and women of a given social group.
      This value will then be divided to the number of ages equaly.

As the output one will get a SQLite database file with `houses`, `social_groups`, `social_groups_distribution`, and `population_divided` tables created and filled.

#### Social groups concept explanation

A person can have exactly one **primary social group**. However, that person can still be a member of a multiple **additional social group**s.

For example, one can define following primary social groups: "Children (0-11 y.o.)", "Teenagers (12-18 y.o.)", "Students (19-26 y.o.)", "Working adults (19-26 y.o.)",
  "Workless adults (19-26 y.o.)". The last three groups intersect in the age range, which means that in this model a person of 19-26 years old can be either
  student, working adult or an adult witout work.

Following additional social groups can be used: "Dog owners", "Bike riders", "Christians". One person can be in all of the three groups while being in
  exactly one primary social group.

#### Launch example:

```bash
population-restore divide -h sample_data/divider/houses.csv -s sample_data/divider/social_groups.json -oi output/houses_with_ids.csv -o output/houses_divided.sqlite
```

This is a small example to get the point. There are 4 social groups: 2 pimary and 2 additional, people age is from 0 to 3 (which mean that they are born with
  age 0 and die at age 4).

where:
- -h - path to houses file (geojson, json, csv or xlsx)
- -s - path to social groups configuration json file
- -oi - path for a copy of input houses with `id` attribute added (if it was missing, to distinguish houses in output sqlite database)
- -o - path for output houses people division SQLite database

### Divided population propagation

The next step available is a modeling of a future population for a given amount of years.

You will need to set following data:
- houses with divided population and load, social groups and their probability distribution (SQLite database got from **dividing** part)
- survivability coefficients file - json with "men" and "women" attributes, each being an array of
  floats - **i**ih position means probability for a person to "survive" from year **i** to **i+1**
- boys_to_girls coefficient value
- fertility coefficient value
- fertility period begin and end years values

#### Launch example:

```bash
population-restore forecast -h output/houses_divided.sqlite -s sample_data/forecaster/survivability_coefficients.json -o output/forecaster -b 2020 -n 10 -btg 1.06 -fc 1.0723 -fb 1 -fe 3
```
In this example ages range is from 0 to 3, so survivability coefficients have 3 values for both men and women. For the population to survive the fertility
  coefficient is set to 1.07 baby per woman, and women are considered fertil from age 1 to 3.
