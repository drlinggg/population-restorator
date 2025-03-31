"""todo"""

from __future__ import annotations
import traceback
import sys

from loguru import logger
import pandas as pd
import sqlite3
import numpy as np


def export_year_age_values(db_path: str, territory_id: int, verbose: bool) -> pd.DataFrame | None:
    try:
        database = sqlite3.connect(db_path)
    except Exception as exc:  # pylint: disable=broad-except
        logger.critical("Exception on connecting to db: {!r}", exc)
        if verbose:
            traceback.print_exc()
        sys.exit(1)

    cur = database.cursor()
    try:
        result = cur.execute(
            f"SELECT house_id, age, sum(men), sum(women) "
            f"FROM population_divided "
            f"WHERE territory_id == {territory_id} "
            f"GROUP BY house_id, age"
        ).fetchall()

        columns = ["house_id", "age", "men", "women"]
        return pd.DataFrame(np.array(result), columns=columns)

    except Exception as e:
        print(f"Error executing query: {e}")
        return None
    finally:
        database.close()
