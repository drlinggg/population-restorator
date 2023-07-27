"""Logic of exporting pandas DataFrame to GeoJSON is defined here."""
from __future__ import annotations

import json
from typing import Any, BinaryIO, Literal, TextIO

import numpy as np
import pandas as pd
from loguru import logger


class NpEncoder(json.JSONEncoder):
    """JSON encoder to use with numpy/pandas datatypes."""

    def default(self, o: Any) -> Any:
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return int(o) if o.is_integer() else float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)


def to_geojson(
    dataframe: pd.DataFrame,
    filename_or_buf: str | TextIO,
) -> None:
    """Export pandas DataFrame to GeoJSON format.

    Args:
        dataframe (DataFrame): pandas DataFrame to export.
        filename_or_buf (str | TextIO): filename or StringIO buffer.
    """
    logger.debug("Saving geojson" + (f' to "{filename_or_buf}"' if isinstance(filename_or_buf, str) else ""))

    geometry_series = dataframe["geometry"]
    dataframe = dataframe.drop("geometry", axis=1)

    for col in set(dataframe.columns):
        if isinstance(dataframe[col], pd.DataFrame):
            logger.warning(f'Table contains multiple columns having with the same name: "{col}", renaming')
            overlapping_columns_number_range = iter(range(dataframe.shape[1] + 1))
            dataframe = dataframe.rename(
                lambda name, col=col, rng=overlapping_columns_number_range: name
                if name != col
                else f"{col}_{next(rng)}",
                axis=1,
            )

    if dataframe.shape[0] > 0:
        for i in range(dataframe.shape[1]):
            dataframe.iloc[:, i] = pd.Series(
                list(
                    map(
                        lambda x: int(x) if isinstance(x, float) and x.is_integer() else x,
                        dataframe.iloc[:, i],
                    )
                ),
                dtype=object,
            )
    dataframe = dataframe.replace({np.nan: None})

    geojson = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:EPSG::4326",
            },
        },
        "features": [
            {
                "type": "Feature",
                "properties": dict(row),
                "geometry": geometry,
            }
            for (_, row), geometry in zip(dataframe.iterrows(), geometry_series)
        ],
    }
    if isinstance(filename_or_buf, str):
        geojson["name"] = filename_or_buf
        with open(filename_or_buf, "w", encoding="utf-8") as file:
            json.dump(geojson, file, ensure_ascii=False, cls=NpEncoder)
    else:
        json.dump(geojson, filename_or_buf, ensure_ascii=False, cls=NpEncoder)


def to_json(dataframe: pd.DataFrame, filename_or_buf: str | TextIO) -> None:
    """Export pandas DataFrame to json format.

    Args:
        dataframe (DataFrame): pandas DataFrame to export.
        filename_or_buf (str | TextIO): filename or StringIO buffer.
    """
    logger.debug("Saving json" + f' to "{filename_or_buf}"' if isinstance(filename_or_buf, str) else "")
    dataframe = dataframe.copy()

    for col in set(dataframe.columns):
        if isinstance(dataframe[col], pd.DataFrame):
            logger.warning(f'Table has more than one column with the same name: "{col}", renaming')
            overlapping_columns_number_range = iter(range(dataframe.shape[1] + 1))
            dataframe = dataframe.rename(
                lambda name, col=col, rng=overlapping_columns_number_range: name
                if name != col
                else f"{col}_{next(rng)}",
                axis=1,
            )

    for i in range(dataframe.shape[1]):
        dataframe.iloc[:, i] = pd.Series(
            list(
                map(
                    lambda x: int(x) if isinstance(x, float) and x.is_integer() else x,
                    dataframe.iloc[:, i],
                )
            ),
            dtype=object,
        )
    dataframe = dataframe.replace({np.nan: None})
    data: list[dict[str, Any]] = [dict(row) for _, row in dataframe.iterrows()]
    if isinstance(filename_or_buf, str):
        with open(filename_or_buf, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4, cls=NpEncoder)
    else:
        json.dump(data, filename_or_buf, ensure_ascii=False, cls=NpEncoder)


def to_csv(dataframe: pd.DataFrame, filename_or_buf: str | TextIO) -> None:
    """Export pandas DataFrame to csv format.

    Args:
        dataframe (DataFrame): pandas DataFrame to export.
        filename_or_buf (str | TextIO): filename or StringIO buffer.
    """
    logger.debug("Saving csv" + f' to "{filename_or_buf}"' if isinstance(filename_or_buf, str) else "")

    dataframe = dataframe.copy()
    for i in range(dataframe.shape[1]):
        dataframe.iloc[:, i] = pd.Series(
            map(
                lambda x: int(x) if isinstance(x, float) and x.is_integer() else x,
                dataframe.iloc[:, i],
            ),
            dtype=object,
        )
    dataframe = dataframe.replace({np.nan: None})
    dataframe.to_csv(filename_or_buf, header=True, index=False)


def to_excel(dataframe: pd.DataFrame, filename_or_buf: str | BinaryIO) -> None:
    """Export pandas DataFrame to excel format.

    Args:
        dataframe (DataFrame): pandas DataFrame to export.
        filename_or_buf (str | BinaryIO): filename or BytesIO buffer.
    """
    logger.debug("Saving excel" + (f" to {filename_or_buf}" if isinstance(filename_or_buf, str) else ""))

    dataframe = dataframe.copy()
    for i in range(dataframe.shape[1]):
        dataframe.iloc[:, i] = pd.Series(
            map(
                lambda x: int(x) if isinstance(x, float) and x.is_integer() else x,
                dataframe.iloc[:, i],
            ),
            dtype=object,
        )
    dataframe = dataframe.replace({np.nan: None})
    if isinstance(filename_or_buf, str):
        dataframe.to_excel(filename_or_buf, header=True, index=False)
    else:
        with pd.ExcelWriter(filename_or_buf) as writer:  # pylint: disable=abstract-class-instantiated
            dataframe.to_excel(writer, header=True, index=False)


def to_file(
    dataframe: pd.DataFrame,
    filename: str,
):
    """Export pandas DataFrame to the file given by filename.

    Args:
        dataframe (pd.DataFrame): DataFrame to export.
        filename (str): Filename to export DataFrame to.
    """
    if "." not in filename:
        logger.warning("File does not have extension, using csv")
        filename += ".csv"
    file_format = filename.split(".")[-1].lower()
    if file_format.lower() not in ("csv", "xlsx", "json", "geojson"):
        logger.error(f'File has wrong extension ("{file_format}"), switching to .csv')
        filename += ".csv"
        file_format = "csv"

    if file_format == "csv":
        to_csv(dataframe, filename)
    elif file_format == "xlsx":
        to_excel(dataframe, filename)
    elif file_format == "geojson":
        to_geojson(dataframe, filename)
    elif file_format == "json":
        to_json(dataframe, filename)


def to_buffer(
    dataframe: pd.DataFrame,
    buffer: TextIO | BinaryIO,
    file_format: Literal["csv", "xlsx", "geojson", "json"],
) -> None:
    """Export pandas DataFrame to buffer.

    Args:
        dataframe (pd.DataFrame): DataFrame to export.
        buffer (TextIO | BinaryIO): StringIO (for csv, json, geojson) or BytesIO (for xlsx) to export DataFrame to.
        format (Literal["csv", "xlsx", "geojson", "json"]): file format to export to buffer.
    """
    file_format = file_format.lower()
    if file_format not in ("csv", "xlsx", "json", "geojson"):
        logger.error(f'Format is not supported ("{file_format}"), switching to csv')
        file_format = "csv"
    logger.info(f"Saving file in {file_format} format")

    if file_format == "csv":
        to_csv(dataframe, buffer)
    elif file_format == "xlsx":
        to_excel(dataframe, buffer)
    elif file_format == "geojson":
        to_geojson(dataframe, buffer)
    elif file_format == "json":
        to_json(dataframe, buffer)
