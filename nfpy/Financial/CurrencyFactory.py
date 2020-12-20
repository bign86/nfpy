#
# Handler of currency changes
#

import pandas as pd

from nfpy.Assets import get_af_glob
from nfpy.Configuration import get_conf_glob
import nfpy.DB as DB
from nfpy.Tools import (Singleton, Exceptions as Ex)


# TODO: This makes the inversion every time, we could store two different
#       series with inversion already performed for speed at the expense
#       of more memory usage
class Conversion(object):
    """ Object that wraps the currency asset for conversions. """

    def __init__(self, uid: str, obj, invert: bool):
        self._uid = uid
        self._obj = obj
        self._invert = invert

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def prices(self) -> pd.Series:
        p = self._obj.prices
        if self._invert:
            p = 1. / p
        return p

    @property
    def returns(self) -> pd.Series:
        r = self._obj.returns
        if self._invert:
            r = -r / (r + 1.)
        return r

    @property
    def log_returns(self) -> pd.Series:
        r = self._obj.log_returns
        if self._invert:
            r = -r
        return r

    def get(self, dt: pd.Timestamp) -> float:
        idx = self.prices.loc[:dt].last_valid_index()
        return self.prices.at[idx]


class DummyConversion(Conversion):

    def __init__(self):
        super().__init__('Dummy', None, False)

    @property
    def prices(self) -> float:
        return 1.

    @property
    def returns(self) -> float:
        return .0

    @property
    def log_returns(self) -> float:
        return .0

    def get(self, dt: pd.Timestamp) -> float:
        return 1.


class CurrencyFactory(metaclass=Singleton):
    """ Handles currency exchanges. """

    _TABLE = 'Currency'
    _KNOWN_CCY = ['EUR', 'USD', 'GBP', 'CHF', 'CAD', 'ZAR', 'AUD', 'YEN', 'NWK',
                  'ARS', 'HKD', 'NZD', 'TRY', 'RUB']
    _BASE_CCY = ['EUR', 'USD', 'GBP', 'CHF']

    def __init__(self):
        self._af = get_af_glob()
        self._qb = DB.get_qb_glob()
        self._db = DB.get_db_glob()

        self._dict_ccy = {}

        base_ccy = get_conf_glob().base_ccy
        self._base_ccy = self._validate_ccy(base_ccy)

    @property
    def base_ccy(self) -> str:
        return self._base_ccy

    @base_ccy.setter
    def base_ccy(self, v: str):
        self._base_ccy = self._validate_ccy(v)

    def is_ccy(self, v: str) -> bool:
        return v in self._KNOWN_CCY

    def is_base_ccy(self, v: str) -> bool:
        return v in self._BASE_CCY

    def _validate_ccy(self, v: str) -> str:
        if v not in self._KNOWN_CCY:
            raise ValueError('Currency {} not recognized'.format(v))
        return v

    def _validate_base_ccy(self, v: str) -> str:
        if v not in self._BASE_CCY:
            raise ValueError('Currency {} not recognized'.format(v))
        return v

    def get(self, src_ccy: str, tgt_ccy: str = None) -> Conversion:
        """ Get the conversion object.

            Input:
                src_ccy [str]: starting currency
                tgt_ccy [str]: target currency (default Base currency)

            Output:
                fxc [Conversion]: Conversion object
        """
        tgt_ccy = self._base_ccy if tgt_ccy is None else tgt_ccy
        if src_ccy == tgt_ccy:
            return DummyConversion()

        try:
            fxc = self._dict_ccy[(src_ccy, tgt_ccy)]
        except KeyError:
            self._fetch_obj_fx(src_ccy, tgt_ccy)
            fxc = self._dict_ccy[(src_ccy, tgt_ccy)]
        return fxc

    def apply(self, v: pd.Series, src_ccy: str, tgt_ccy: str) -> pd.Series:
        if src_ccy == tgt_ccy:
            return v
        return v

    def _fetch_obj_fx(self, src_ccy: str, tgt_ccy: str):
        """ Fetch the exchange object for the given currencies. """
        q = self._qb.select(self._TABLE, fields=['uid'], keys=['base_fx', 'tgt_fx'])

        # Search for the currency direct
        invert = False
        res = self._db.execute(q, (src_ccy, tgt_ccy)).fetchall()
        if len(res) > 1:
            raise ValueError('Too many currencies fetched, check database!')

        elif not res:
            # No results, search for the currency inverted
            invert = True
            res = self._db.execute(q, (tgt_ccy, src_ccy)).fetchall()
            if len(res) > 1:
                raise ValueError('Too many currencies fetched, check database!')

            if not res:
                # The conversion is not in the database in any way
                raise Ex.MissingData('Currency {} -> {} not found in database'
                                     .format(tgt_ccy, src_ccy))

        uid = res[0][0]
        obj_fx = self._af.get(uid)
        self._dict_ccy[(src_ccy, tgt_ccy)] = Conversion(uid, obj_fx, invert)
        self._dict_ccy[(tgt_ccy, src_ccy)] = Conversion(uid, obj_fx, not invert)


def get_fx_glob() -> CurrencyFactory:
    """ Returns the pointer to the global Currency Handler """
    return CurrencyFactory()
