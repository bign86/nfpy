#
# Rate factory class
# Class to handle rate and curves
#

import warnings
from itertools import groupby

from nfpy.Assets import get_af_glob
import nfpy.DB as DB
from nfpy.Tools import (Singleton, Exceptions as Ex)


class RateFactory(metaclass=Singleton):
    """ Factory to handle rates and curves. """

    _CURVE_TABLE = 'Curve'
    _RATE_TABLE = 'Rate'
    _Q_GET_RF = f'select c.currency, r.uid from Rate as r join CurveConstituents' \
                f' as cc on r.uid = cc.bucket join Curve as c on c.uid = cc.uid' \
                f' where r.is_rf = True;'
    _Q_SET_RF = 'update Rate set is_rf = ? where uid = ?;'

    def __init__(self):
        self._db = DB.get_db_glob()
        self._qb = DB.get_qb_glob()
        self._af = get_af_glob()
        self._rf = {}
        
        self._initialize()
    
    def _initialize(self):
        res = self._db.execute(self._Q_GET_RF).fetchall()
        if not res:
            raise Ex.MissingData('No risk free found in the database')

        # Consistency check to ensure a single rf for currency is defined
        res = sorted(res, key=lambda f: f[0])
        for k, g in groupby(res, key=lambda f: f[0]):
            n = len(list(g))
            if n > 1:
                raise ValueError(f'{n} risk free defined for {k}')

        self._rf = {t[0]: t[1] for t in res}

    def get_rf(self, ccy: str):
        try:
            uid = self._rf[ccy]
        except KeyError:
            raise Ex.MissingData(f'No risk free set for currency {ccy}')
        return self._af.get(uid)

    def set_rf(self, ccy: str, rate: str):
        """ Set a risk free rate. """
        data = [(True, rate)]
        if ccy in self._rf:
            old_rate = self._rf[ccy]
            data.append((False, old_rate))
            msg = f'The rate {old_rate} is set as current risk free and will be overridden'
            warnings.warn(msg)

        self._db.executemany(self._Q_SET_RF, data, commit=True)


def get_rf_glob() -> RateFactory:
    """ Returns the pointer to the global RateFactory """
    return RateFactory()
