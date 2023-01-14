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

    def __init__(self, uid: str, obj, invert: bool, src_f: float, tgt_f: float):
        self._uid = uid
        self._obj = obj
        self._invert = invert
        self._peg_f = src_f/tgt_f

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def prices(self) -> pd.Series:
        p = self._obj.prices * self._peg_f
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

    def __init__(self, uid: str, invert: bool, src_f: float, tgt_f: float):
        super().__init__(uid, None, invert, src_f, tgt_f)

    @property
    def prices(self) -> float:
        if self._invert:
            return 1. / self._peg_f
        else:
            return self._peg_f

    @property
    def returns(self) -> float:
        return .0

    @property
    def log_returns(self) -> float:
        return .0

    def get(self, dt: pd.Timestamp) -> float:
        if self._invert:
            return 1. / self._peg_f
        else:
            return self._peg_f


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

    def _create_obj_fx(self, src_ccy: str, tgt_ccy: str) -> None:

        # Check whether src is pegged
        src_data = self._known_ccy[src_ccy]
        if src_data[3] is not None:
            src_fetch, src_factor = src_data[3:5]
        else:
            src_fetch, src_factor = src_ccy, 1.

        # Check whether tgt is pegged
        tgt_data = self._known_ccy[tgt_ccy]
        if tgt_data[3] is not None:
            tgt_fetch, tgt_factor = tgt_data[3:5]
        else:
            tgt_fetch, tgt_factor = tgt_ccy, 1.

        # If I should convert the pegged to the peggee, a dummy is returned
        if src_fetch == tgt_fetch:
            # Create the FX object
            self._dict_fx[(src_ccy, tgt_ccy)] = DummyConversion(
                f'{src_ccy}|{tgt_ccy}', True, src_factor, tgt_factor
            )
            self._dict_fx[(tgt_ccy, src_ccy)] = DummyConversion(
                f'{src_ccy}|{tgt_ccy}', False, src_factor, tgt_factor
            )
            return

        # Fetch required currencies
        # Search for the currency direct
        invert = False
        res = self._db.execute(
            self._q_fetch,
            (src_fetch, tgt_fetch)
        ).fetchall()
        if len(res) > 1:
            raise ValueError('Too many currencies fetched, check database!')

        # No results, search for the currency inverted
        elif not res:
            invert = True
            res = self._db.execute(
                self._q_fetch,
                (tgt_fetch, src_fetch)
            ).fetchall()
            if len(res) > 1:
                raise ValueError('Too many currencies fetched, check database!')

            if not res:
                # The conversion is not in the database in any way
                msg = f'Currency {tgt_fetch} -> {src_fetch} not found in database'
                raise Ex.MissingData(msg)

        uid = res[0][0]
        obj_fx = self._af.get(uid)

        # Create the FX object
        self._dict_fx[(src_ccy, tgt_ccy)] = Conversion(
            f'{src_ccy}|{tgt_ccy}',
            obj_fx, invert, src_factor, tgt_factor
        )
        self._dict_fx[(tgt_ccy, src_ccy)] = Conversion(
            f'{src_ccy}|{tgt_ccy}',
            obj_fx, not invert, src_factor, tgt_factor
        )

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

    @property
    def base_ccy(self) -> str:
        return self._base_ccy

    @base_ccy.setter
    def base_ccy(self, v: str) -> None:
        self._base_ccy = self._validate_ccy(v)

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
            return DummyConversion(src_ccy, False, 1., 1.)

        selection = (src_ccy, tgt_ccy)
        try:
            fxc = self._dict_fx[selection]
        except KeyError:
            self._create_obj_fx(*selection)
            fxc = self._dict_fx[selection]
        return fxc

    def is_ccy(self, v: str) -> bool:
        return v in self._known_ccy

    def is_pegged(self, ccy: str) -> bool:
        return self._known_ccy[ccy][3] is not None


def get_fx_glob() -> FxFactory:
    """ Returns the pointer to the global Fx Factory. """
    return FxFactory()
