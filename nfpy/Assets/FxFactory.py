#
# Handler of currency exchange rates
#

import pandas as pd
from typing import Optional

import nfpy.DB as DB
from nfpy.Tools import (
    Exceptions as Ex,
    get_conf_glob,
    Singleton,
)

from . import get_af_glob


# TODO: This makes the inversion every time, but we could store two series
#       with inversion performed for speed at the expense of memory usage.
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


class FxFactory(metaclass=Singleton):
    """ Handles currency exchange rates. """

    _T_FX = 'Fx'
    _T_CURRENCIES = 'Currency'

    def __init__(self):
        self._af = get_af_glob()
        self._qb = DB.get_qb_glob()
        self._db = DB.get_db_glob()

        self._dict_fx = {}

        self._known_ccy = {
            ccy[1]: ccy for ccy in
            self._db.execute(f'select * from {self._T_CURRENCIES}')
                .fetchall()
        }
        self._q_fetch = self._qb.select(
            self._T_FX,
            fields=('uid',),
            keys=('price_ccy', 'base_ccy')
        )
        self._base_ccy = self._validate_ccy(
            get_conf_glob().base_ccy
        )

    @property
    def base_ccy(self) -> str:
        return self._base_ccy

    @base_ccy.setter
    def base_ccy(self, v: str) -> None:
        self._base_ccy = self._validate_ccy(v)

    def _fetch_obj_fx(self, src_ccy: str, tgt_ccy: str) -> None:
        """ Fetch the exchange object for the given currencies. """
        # Search for the currency direct
        invert = False
        res = self._db.execute(
            self._q_fetch,
            (src_ccy, tgt_ccy)
        ).fetchall()
        if len(res) > 1:
            raise ValueError('Too many currencies fetched, check database!')

        elif not res:
            # No results, search for the currency inverted
            invert = True
            res = self._db.execute(
                self._q_fetch,
                (tgt_ccy, src_ccy)
            ).fetchall()
            if len(res) > 1:
                raise ValueError('Too many currencies fetched, check database!')

            if not res:
                # The conversion is not in the database in any way
                msg = f'Currency {tgt_ccy} -> {src_ccy} not found in database'
                raise Ex.MissingData(msg)

        uid = res[0][0]
        obj_fx = self._af.get(uid)
        self._dict_fx[(src_ccy, tgt_ccy)] = Conversion(uid, obj_fx, invert)
        self._dict_fx[(tgt_ccy, src_ccy)] = Conversion(uid, obj_fx, not invert)

    def _validate_ccy(self, v: str) -> str:
        if v not in self._known_ccy:
            raise Ex.MissingData(f'Currency {v} not recognized')
        return v

    # TODO: to be implemented
    @staticmethod
    def apply(v: pd.Series, src_ccy: str, tgt_ccy: str) -> pd.Series:
        RuntimeWarning('Not implemented')
        if src_ccy == tgt_ccy:
            return v
        return v

    def get_ccy(self, v: str) -> tuple[str]:
        """ Get a currency information. """
        return self._known_ccy[v]

    def get(self, src_ccy: str, tgt_ccy: Optional[str] = None) -> Conversion:
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

        selection = (src_ccy, tgt_ccy)
        try:
            fxc = self._dict_fx[selection]
        except KeyError:
            self._fetch_obj_fx(*selection)
            fxc = self._dict_fx[selection]
        return fxc

    def is_ccy(self, v: str) -> bool:
        return v in self._known_ccy


def get_fx_glob() -> FxFactory:
    """ Returns the pointer to the global Fx Factory. """
    return FxFactory()
