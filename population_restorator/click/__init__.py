"""Click cli launchnig options are located here.
"""
from population_restorator.utils.dotenv import read_envfile


read_envfile()

from .balancer import balance  # pylint: disable=wrong-import-position; isort: skip
from .divider import divide  # pylint: disable=wrong-import-position; isort: skip
from .forecaster import forecast  # pylint: disable=wrong-import-position; isort: skip
from .main_group import main  # pylint: disable=wrong-import-position; isort: skip


__all__ = [
    "main",
]
