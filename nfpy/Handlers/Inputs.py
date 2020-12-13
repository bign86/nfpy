#
# Handler of Inputs
#

import re
from datetime import datetime
from typing import Union, List, Any
import pandas as pd

from nfpy.Handlers.AssetFactory import get_af_glob
from nfpy.Handlers.Calendar import date_2_datetime
from nfpy.Handlers.CurrencyFactory import get_fx_glob
from nfpy.Tools.Constants import KNOWN_COUNTRIES

SQLITE2PY_CONVERSION = {
    'TEXT': 'str',
    'INT': 'int',
    'INTEGER': 'int',
    'FLOAT': 'float',
    'REAL': 'float',
    'NUMERIC': 'int',
    'DATE': 'datetime',
    'DATETIME': 'datetime',
    'BOOL': 'bool',
}


class InputHandler(object):
    """ Object to handle inputs and wrapping all relevant input and input
        validation methods.
    """

    _DEFAULT_SEP = ','

    def __init__(self):
        self._af = get_af_glob()
        self._ccy = get_fx_glob()
        self._converters = {'str': self._to_string, 'float': self._to_float,
                            'int': self._to_int, 'bool': self._to_bool,
                            'uid': self._to_string, 'datetime': self._to_datetime,
                            'currency': self._to_string, 'timestamp': self._to_timestamp,
                            'country': self._to_string}
        self._validators = {'uid': self._check_uid, 'currency': self._check_ccy,
                            'isin': self._check_isin, 'country': self._check_country}

    @staticmethod
    def _to_int(v: str, **kwargs) -> int:
        _ = kwargs
        return int(v)

    @staticmethod
    def _to_float(v: str, **kwargs) -> float:
        _ = kwargs
        return float(v)

    @staticmethod
    def _to_bool(v: str, **kwargs) -> bool:
        _ = kwargs
        return True if v.lower() in ('y', 'yes', '1', 'true') else False

    @staticmethod
    def _to_string(v: str, **kwargs) -> str:
        _ = kwargs
        return re.sub('[!@#$?*;,:+]', '', v)

    def _check_uid(self, uid: str) -> tuple:
        """ Validate a candidate uid checking existence. """
        if not self._af.exists(uid):
            return False, 'Uid not found'
        return True, 'Ok'

    def _check_ccy(self, v: str) -> tuple:
        """ Validate a candidate currency checking existence. """
        if not self._ccy.is_ccy(v):
            return False, 'Currency not recognized'
        return True, 'Ok'

    @staticmethod
    def _check_country(v: str) -> tuple:
        """ Validate a candidate country checking existence. """
        if v not in KNOWN_COUNTRIES:
            return False, 'Country not recognized'
        return True, 'Ok'

    @staticmethod
    def _check_isin(v: str) -> tuple:
        """ Validate a candidate isin format. """
        pattern = re.compile("^([a-zA-Z]{2}[a-zA-Z0-9]{9}[0-9])$")
        if not pattern.match(v):
            return False, 'ISIN malformed'
        return True, 'Ok'

    @staticmethod
    def _to_timestamp(v: str, **kwargs) -> pd.Timestamp:
        """ Transforms a date from string to pandas timestamp.

            Input:
                v [str]: date in string format
                kwargs [dict]: 'fmt' argument to specify the date format

            Output:
                date [pd.Timestamp]: formatted date
        """
        return pd.to_datetime(v, format=kwargs['fmt'])

    @staticmethod
    def _to_datetime(v: str, **kwargs) -> datetime.date:
        """ Transforms a date from string to datetime.

            Input:
                v [str]: date in string format
                kwargs [dict]: 'fmt' argument to specify the date format

            Output:
                date [datetime.date]: formatted date
        """
        return date_2_datetime(v, fmt=kwargs['fmt'])

    def _convert(self, vin: str, idesc: str, **kwargs) \
            -> Union[List, str, int, float, bool, pd.Timestamp, datetime.date]:
        """ Converts the supplied input by cleaning the string and casting to the
            appropriate data type. An exception is cast if casting is impossible or
            if inputs are empty.
        """
        if not isinstance(vin, str):
            raise TypeError("Only string are accepted as inputs in input validation")

        is_list = kwargs['is_list'] if 'is_list' in kwargs else False
        sep = kwargs['sep'] if 'sep' in kwargs else self._DEFAULT_SEP
        fmt = kwargs['fmt'] if 'fmt' in kwargs else '%Y-%m-%d'

        try:
            cf = self._converters[idesc]
        except KeyError:
            raise KeyError('Input descriptor {} not recognized'.format(idesc))

        try:
            if is_list:
                v_out = [cf(c.lstrip().rstrip(), fmt=fmt) for c in vin.split(sep)]
            else:
                v_out = cf(vin, fmt=fmt)
        except TypeError:
            raise TypeError("Cannot convert input")
        except ValueError as e:
            raise e

        return v_out

    def _validate(self, value: Any, checker: str) -> tuple:
        try:
            valf = self._validators[checker]
        except KeyError:
            raise KeyError('Input descriptor {} not recognized'.format(checker))
        return valf(value)

    def input(self, msg: str, idesc: str = 'str', optional: bool = False,
              default: Any = None, checker: str = None, **kwargs) \
            -> Union[str, int, float, list, bool, pd.Timestamp, datetime.date]:
        """ Validates the supplied input by cleaning the string and casting to the
            appropriate data type. An exception is cast if casting is impossible or
            if inputs are empty.

            Input:
                vin [str]: input string as given by the user
                idesc [str]: converted type (default str)
                default [Any]: default input value (default None)
                checker [Any]: check function (default None)
                sep [str]: list separator (default comma ',')
                fmt [str]: format string for dates (default %Y-%m-%d)
                is_list [bool]: true if list in input (default False)

            Output:
                vout [Union[str, int, float, list, bool]]: value validated

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
                print('*** Mandatory ***')
            elif (not _v) and (optional is True):
                _validated = True
            else:
                value = self._convert(_v, idesc, **kwargs)
                if checker:
                    _validated, msg_out = self._validate(value, checker)
                    if not _validated:
                        print('*** Not valid: {}'.format(msg_out))
                else:
                    _validated = True
        return value
