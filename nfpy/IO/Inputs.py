#
# Handler of Inputs
#

import json
import pandas as pd
import re
from typing import (Any, Optional)

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.Downloader as Dwn
from nfpy.Tools import (Constants as Cn, Exceptions as Ex, Utilities as Ut)


class InputHandler(object):
    """ Object to handle inputs and wrapping all relevant input and input
        validation methods.
    """

    _DEFAULT_SEP = ','

    def __init__(self):
        self._af = Ast.get_af_glob()
        self._ccy = Ast.get_fx_glob()
        self._dwn = Dwn.get_dwnf_glob()
        self._qb = DB.get_qb_glob()
        self._converters = {
            'str': self._to_string, 'float': self._to_float,
            'int': self._to_int, 'bool': self._to_bool,
            'uid': self._to_uid, 'datetime': self._to_datetime,
            'currency': self._to_ccy, 'timestamp': self._to_timestamp,
            'country': self._to_country, 'dict': self._to_json,
            'json': self._to_json, 'uint': self._to_uint,
            'index': self._to_index, 'isin': self._to_isin,
            'date': self._to_date, 'table': self._to_table,
        }

    @staticmethod
    def _to_bool(v: str, **kwargs) -> bool:
        _ = kwargs
        return Ut.to_bool(v)

    def _to_ccy(self, v: str, **kwargs) -> str:
        ccy = self._to_string(v)
        if not self._ccy.is_ccy(ccy):
            raise Ex.InputHandlingError(f'InputHandler(): currency {ccy} not recognized')
        return ccy

    def _to_country(self, v: str, **kwargs) -> str:
        country = self._to_string(v)
        if country not in Cn.KNOWN_COUNTRIES:
            raise Ex.InputHandlingError(f'InputHandler(): country {country} not recognized')
        return country

    @staticmethod
    def _to_date(v: str, **kwargs) -> Cal.TyTime:
        """ Transforms a date from string to datetime.

            Input:
                v [str]: date in string format
                kwargs [dict]: 'fmt' argument to specify the date format

            Output:
                date [datetime.date]: formatted date
        """
        return Cal.date_2_datetime(v, fmt=kwargs['fmt'])

    @staticmethod
    def _to_datetime(v: str, **kwargs) -> Cal.TyTime:
        """ Transforms a date from string to datetime.

            Input:
                v [str]: date in string format
                kwargs [dict]: 'fmt' argument to specify the date format

            Output:
                date [datetime.date]: formatted date
        """
        return Cal.date_2_datetime(v, fmt=kwargs['fmt'])

    @staticmethod
    def _to_float(v: str, **kwargs) -> float:
        _ = kwargs
        return float(v)

    def _to_index(self, v: str, limits: Any, **kwargs) -> int:
        num = self._to_int(v)
        if (limits[0] > num) or (num > limits[1]):
            raise Ex.InputHandlingError(f'InputHandler(): {num} out of limits')
        return num

    @staticmethod
    def _to_int(v: str, **kwargs) -> int:
        _ = kwargs
        return int(v)

    def _to_isin(self, v: str, **kwargs) -> str:
        isin = self._to_string(v)
        pattern = re.compile("^([a-zA-Z]{2}[a-zA-Z0-9]{9}[0-9])$")
        if not pattern.match(isin):
            raise Ex.InputHandlingError(f'InputHandler(): {isin} malformed')
        return isin

    def _to_provider(self, v: str, **kwargs) -> str:
        prov = self._to_string(v)
        if not self._dwn.provider_exists(prov):
            raise Ex.InputHandlingError(f'InputHandler(): provider {prov} not recognized')
        return prov

    @staticmethod
    def _to_string(v: str, **kwargs) -> str:
        _ = kwargs
        return re.sub('[!@#$?*;:+]', '', v)

    def _to_table(self, v: str, **kwargs) -> str:
        table = self._to_string(v)
        if not self._qb.exists_table(table):
            raise Ex.InputHandlingError(f'InputHandler(): table {table} not recognized')
        return table

    @staticmethod
    def _to_timestamp(v: str, **kwargs) -> Cal.TyDate:
        """ Transforms a date from string to pandas timestamp.

            Input:
                v [str]: date in string format
                kwargs [dict]: 'fmt' argument to specify the date format

            Output:
                date [pd.Timestamp]: formatted date
        """
        return pd.to_datetime(v, format=kwargs['fmt'])

    @staticmethod
    def _to_json(v: str, **kwargs) -> Any:
        _ = kwargs
        return json.loads(v)

    def _to_uid(self, v: str, **kwargs) -> str:
        uid = self._to_string(v)
        if not self._af.exists(uid):
            raise Ex.InputHandlingError(f'InputHandler(): {uid} not found')
        return uid

    @staticmethod
    def _to_uint(v: str, **kwargs) -> int:
        _ = kwargs
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
            raise TypeError("Only string are accepted as inputs in input validation")

        is_list = kwargs['is_list'] if 'is_list' in kwargs else False
        sep = kwargs['sep'] if 'sep' in kwargs else self._DEFAULT_SEP
        fmt = kwargs['fmt'] if 'fmt' in kwargs else '%Y-%m-%d'

        try:
            cf = self._converters[idesc]
        except KeyError:
            raise KeyError(f'Input descriptor {idesc} not recognized')

        try:
            if is_list:
                v_out = [
                    cf(c.lstrip().rstrip(), fmt=fmt, limits=limits)
                    for c in vin.split(sep)
                ]
            else:
                v_out = cf(vin, fmt=fmt, limits=limits)
        except (TypeError, ValueError) as ex:
            raise Ex.InputHandlingError("Cannot convert input")

        return v_out

    def input(self, msg: str, idesc: str = 'str', optional: bool = False,
              default: Optional[Any] = None, limits: Optional[Any] = None,
              **kwargs) -> Any:
        """ Validates the supplied input by cleaning the string and casting to
            the appropriate data type. An exception is cast if casting is
            impossible or if inputs are empty.

            Input:
                msg [str]: message string
                idesc [str]: converted type (default str)
                optional [bool]: whether the input is optional (default False)
                default [Any]: default input value (default None)
                sep [str]: list separator (default comma ',')
                fmt [str]: format string for dates (default %Y-%m-%d)
                is_list [bool]: true if list in input (default False)
                limits [Any]: limits to apply to the converter (default None)

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
