#
# Handler of Inputs
#

import json
import pandas as pd
from typing import Any

import nfpy.Calendar as Cal
from nfpy.Tools import (Constants as Cn, Exceptions as Ex)

from . import Utilities as Ut


class InputHandler(object):
    """ Object to handle inputs and wrapping all relevant input and input
        validation methods.
    """

    _DEFAULT_SEP = ','

    def __init__(self):
        self._converters = {
            'str': Ut.to_string, 'float': float,
            'int': int, 'bool': self._to_bool,
            'uid': self._to_uid, 'datetime': self._to_datetime,
            'currency': self._to_ccy, 'timestamp': self._to_timestamp,
            'country': self._to_country, 'dict': self._to_json,
            'json': self._to_json, 'uint': self._to_uint,
            'index': self._to_index, 'isin': self._to_isin,
            'date': self._to_date, 'table': self._to_table,
        }

    @staticmethod
    def _to_bool(v: str) -> bool:
        parsed = Ut.to_bool(v.lower())
        if parsed is None:
            raise Ex.InputHandlingError(f'InputHandler(): {v} not recognized as boolean')
        else:
            return parsed

    @staticmethod
    def _to_ccy(v: str) -> str:
        from nfpy.Assets import get_fx_glob
        ccy = Ut.to_string(v)
        if not get_fx_glob().is_ccy(ccy):
            raise Ex.InputHandlingError(f'InputHandler(): currency {ccy} not recognized')
        return ccy

    @staticmethod
    def _to_country(v: str) -> str:
        country = Ut.to_string(v)
        if country not in Cn.KNOWN_COUNTRIES:
            raise Ex.InputHandlingError(f'InputHandler(): country {country} not recognized')
        return country

    @staticmethod
    def _to_date(v: str, fmt: str = None) -> Cal.TyDate:
        """ Transforms a date from string to datetime.

            Input:
                v [str]: date in string format
                kwargs [dict]: 'fmt' argument to specify the date format

            Output:
                date [datetime.date]: formatted date
        """
        return Cal.str2d(v, fmt=fmt)

    @staticmethod
    def _to_datetime(v: str, fmt: str = None) -> Cal.TyTime:
        """ Transforms a date from string to datetime.

            Input:
                v [str]: date in string format
                kwargs [dict]: 'fmt' argument to specify the date format

            Output:
                date [datetime.datetime]: formatted date
        """
        return Cal.str2dt(v, fmt=fmt)

    @staticmethod
    def _to_index(v: str, limits: Any = None) -> int:
        num = int(v)
        if (limits[0] > num) or (num > limits[1]):
            raise Ex.InputHandlingError(f'InputHandler(): {num} out of limits')
        return num

    @staticmethod
    def _to_isin(v: str) -> str:
        isin = Ut.to_isin(v)
        if isin is None:
            raise Ex.InputHandlingError(f'InputHandler(): {isin} malformed')
        return isin

    @staticmethod
    def _to_provider(v: str) -> str:
        from nfpy.Downloader import get_dwnf_glob
        prov = Ut.to_string(v)
        if not get_dwnf_glob().provider_exists(prov):
            raise Ex.InputHandlingError(f'InputHandler(): provider {prov} not recognized')
        return prov

    @staticmethod
    def _to_table(v: str) -> str:
        from nfpy.DB import get_qb_glob
        table = Ut.to_string(v)
        if not get_qb_glob().exists_table(table):
            raise Ex.InputHandlingError(f'InputHandler(): table {table} not recognized')
        return table

    @staticmethod
    def _to_timestamp(v: str, fmt: str = None) -> Cal.TyDate:
        """ Transforms a date from string to pandas timestamp.

            Input:
                v [str]: date in string format
                kwargs [dict]: 'fmt' argument to specify the date format

            Output:
                date [pd.Timestamp]: formatted date
        """
        return pd.to_datetime(v, format=fmt)

    @staticmethod
    def _to_json(v: str) -> Any:
        return json.loads(v)

    @staticmethod
    def _to_uid(v: str) -> str:
        from nfpy.Assets import get_af_glob
        uid = Ut.to_string(v)
        if not get_af_glob().exists(uid):
            raise Ex.InputHandlingError(f'InputHandler(): {uid} not found')
        return uid

    @staticmethod
    def _to_uint(v: str) -> int:
        return abs(int(v))

    def _convert(self, vin: str, idesc: str, limits: Any, **kwargs) -> Any:
        """ Converts the supplied input by cleaning the string and casting to
            the appropriate data type. An exception is cast if casting is
            impossible or if inputs are empty.

            Input:
                msg [str]: message string
                idesc [str]: converted type
                limits [Any]: limits to apply to the converter

            Exceptions:
                KeyError: if input descriptor not recognized
                TypeError: non-string input or failed conversion to target
                           data type
                ValueError: if error in conversion of the input
        """
        if not isinstance(vin, str):
            raise Ex.InputHandlingError("InputHandler(): Only string are accepted as inputs in input validation")

        is_list = kwargs['is_list'] if 'is_list' in kwargs else False
        sep = kwargs['sep'] if 'sep' in kwargs else self._DEFAULT_SEP
        fmt = kwargs['fmt'] if 'fmt' in kwargs else '%Y-%m-%d'

        try:
            cf = self._converters[idesc]
        except KeyError:
            raise Ex.InputHandlingError(f'InputHandler(): Input descriptor {idesc} not recognized')

        try:
            if is_list:
                if idesc in ('date', 'datetime', 'timestamp'):
                    v_out = [
                        cf(c.lstrip().rstrip(), fmt)
                        for c in vin.split(sep)
                    ]
                elif idesc == 'index':
                    v_out = [
                        cf(c.lstrip().rstrip(), limits)
                        for c in vin.split(sep)
                    ]
                else:
                    v_out = [
                        cf(c.lstrip().rstrip())
                        for c in vin.split(sep)
                    ]
            else:
                if idesc in ('date', 'datetime', 'timestamp'):
                    v_out = cf(vin, fmt)
                elif idesc == 'index':
                    v_out = cf(vin, limits)
                else:
                    v_out = cf(vin)
        except Ex.InputHandlingError as ex:
            raise ex
        except (TypeError, ValueError) as ex:
            raise Ex.InputHandlingError(f"InputHandler(): Cannot convert input\n{ex}")

        return v_out

    def input(
            self,
            msg: str,
            idesc: str = 'str',
            optional: bool = False,
            default: Any | None = None,
            limits: Any | None = None,
            **kwargs
    ) -> Any:
        """ Validates the supplied input by cleaning the string and casting to
            the appropriate data type. An exception is cast if casting is
            impossible or if inputs are empty.

            Input:
                msg [str]: message string
                idesc [str]: converted type (default str)
                optional [bool | None]: whether the input is optional (default False)
                default [Any | None]: default input value (default None)
                sep [str]: list separator (default comma ',')
                fmt [str]: format string for dates (default %Y-%m-%d)
                is_list [bool]: true if list in input (default False)
                limits [Any | None]: limits to apply to the converter (default None)

            Output:
                out [Union[int, float, list, bool, Cal.TyDate]]: value validated

            Exceptions:
                MissingData: if no input provided
                TypeError: failed conversion to target data type
        """
        _validated = False
        value = None
        while not _validated:
            _v = input(msg).strip()
            if (not _v) and (default is not None):
                value = default
                _validated = True
            elif (not _v) and (optional is False):
                print(f'{Ut.Col.WARNING.value}--- Mandatory {Ut.Col.ENDC.value}')
            elif (not _v) and (optional is True):
                _validated = True
            else:
                try:
                    value = self._convert(_v, idesc, limits, **kwargs)
                except Ex.InputHandlingError as ex:
                    print(f'{Ut.Col.WARNING.value}--- Not valid: {ex.__str__()}{Ut.Col.ENDC.value}')
                else:
                    _validated = True
        return value
