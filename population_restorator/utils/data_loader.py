"""Functions to load pandas.DataFrame from different file types are defined here."""
from __future__ import annotations

import json

import pandas as pd
from loguru import logger
from numpy import nan


def read_geojson(filename: str) -> pd.DataFrame:
    """Load objects as DataFrame from geojson. It contains only [features][properties] columns with geometry."""
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)
        if "features" not in data:
            raise ValueError("Invalid geojson, no 'features' entry")
        res = pd.DataFrame((entry["properties"] | {"geometry": entry["geometry"]}) for entry in data["features"])
        return res.dropna(how="all").reset_index(drop=True).replace({nan: None})


def read_json(filename: str) -> pd.DataFrame:
    """Load objects as DataFrame from json by calling pd.read_json."""
    res: pd.DataFrame = pd.read_json(filename)
    return res.dropna(how="all").reset_index(drop=True).replace({nan: None})  # pylint: disable=no-member


def read_csv(filename: str) -> pd.DataFrame:
    """Load objects as DataFrame from csv by calling pd.read_csv."""
    res: pd.DataFrame = pd.read_csv(filename)
    return res.dropna(how="all").reset_index(drop=True).replace({nan: None})


def read_xlsx(filename: str) -> pd.DataFrame:
    """Load objects as DataFrame from xlsx by calling pd.read_excel
    (requires `openpyxl` Pyhton module installed).
    """
    res: pd.DataFrame = pd.read_excel(filename, engine="openpyxl")
    return res.dropna(how="all").reset_index(drop=True).replace({nan: None})


def read_excel(filename: str) -> pd.DataFrame:
    """Load objects as DataFrame from xls or ods by calling pd.read_excel
    (requires `xlrd` Pyhton module installed for xls and `odfpy` for ods).

    Calls `replace_with_default` after load if `default_values` is present
    """
    res: pd.DataFrame = pd.read_excel(filename)
    return res.dropna(how="all").reset_index(drop=True).replace({nan: None})


_extensions_functions = {
    "csv": read_csv,
    "xlsx": read_xlsx,
    "xls": read_excel,
    "ods": read_excel,
    "json": read_json,
    "geojson": read_geojson,
}


def read_file(filename: str) -> pd.DataFrame:
    """Load objects as DataFrame from the given fie (csv, xlsx, xls, ods, json or geojson)."""

    if (ext := filename[filename.rfind(".") + 1 :].lower()) not in _extensions_functions:
        logger.debug("No readed was found suitable for file type '{}'", ext)
        raise ValueError(f"File extension '{ext}' is not supported")

    logger.debug("Reading '{}'", filename)
    return _extensions_functions[ext](filename)
