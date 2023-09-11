"""Inner database (used in divider and forecaster) information is located here."""
from sqlalchemy import MetaData


__all__ = [
    "metadata",
]

metadata = MetaData()
