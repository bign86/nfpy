#
# DB Types
# Converters adding support to Python types
#

from datetime import datetime
import json
import numpy
import pandas
import sqlite3
from typing import Any


def adapt_np64(val) -> str:
    """ Operates on numpy.datetime64() to obtain a representation to be used
        in sqlite3.
    """
    return str(val).replace('T', ' ')


def adapt_pd_timestamp(val) -> str:
    """ Operates on pandas.Timestamp() to obtain a representation to be used
        in sqlite3.
    """

    return val.isoformat(' ')


def convert_datetime(val) -> datetime:
    """ Converts from DATETIME to datetime.datetime. Taken from the function
        convert_timestamp() in the Python implementation od sqlite3.
    """
    hours, minutes, seconds, microseconds = 0, 0, 0, 0
    parts = val.split(b" ")
    year, month, day = map(int, parts[0].split(b"-"))
    if len(parts) > 1:
        timepart_full = parts[1].split(b".")
        hours, minutes, seconds = map(int, timepart_full[0].split(b":"))
        if len(timepart_full) == 2:
            microseconds = int('{:0<6.6}'.format(timepart_full[1].decode()))

    return datetime(year, month, day, hours, minutes, seconds, microseconds)


def convert_parameters(val) -> Any:
    """ Converts from PARAMETERS to json. """
    return json.loads(val)


# Register the adapters
sqlite3.register_adapter(numpy.datetime64, adapt_np64)
sqlite3.register_adapter(pandas.Timestamp, adapt_pd_timestamp)

# Register the converters
sqlite3.register_converter("DATETIME", convert_datetime)
sqlite3.register_converter("PARAMETERS", convert_parameters)
