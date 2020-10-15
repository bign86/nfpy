#
# Rate factory class
# Class to handle rate and curves
#

import warnings
from itertools import groupby

from nfpy.Assets.Rate import Rate
from nfpy.DB.DB import get_db_glob
from nfpy.Handlers.AssetFactory import get_af_glob
from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Tools.Exceptions import MissingData
from nfpy.Tools.Singleton import Singleton


class RateFactory(metaclass=Singleton):
    """ Factory to handle rates and curves. """

    _CURVE_TABLE = 'Curve'
    _RATE_TABLE = 'Rate'
    _Q_GET_RF = """select c.currency, r.uid from Rate as r join CurveConstituents as cc
on r.uid = cc.bucket join Curve as c on c.uid = cc.uid where r.is_rf = True;"""
    _Q_SET_RF = """update Rate set is_rf = ? where uid = ?;"""

    def __init__(self):
        self._db = get_db_glob()
        self._qb = get_qb_glob()
        self._af = get_af_glob()
        self._rf = {}
        
        self._initialize()
    
    def _initialize(self):
        res = self._db.execute(self._Q_GET_RF).fetchall()
        if not res:
            raise MissingData('No risk free found in the database')

        # Consistency check to ensure a single rf for currency is defined
        res = sorted(res, key=lambda f: f[0])
        for k, g in groupby(res, key=lambda f: f[0]):
            n = len(list(g))
            if n > 1:
                raise ValueError('{} risk free defined for {}'.format(n, k))

        self._rf = {t[0]: t[1] for t in res}

    def get_rf(self, ccy: str) -> Rate:
        try:
            uid = self._rf[ccy]
        except KeyError:
            raise MissingData('No risk free set for currency {}'.format(ccy))
        return self._af.get(uid)

    def set_rf(self, ccy: str, rate: str):
        """ Set a risk free rate. """
        res = self._db.execute(self._Q_GET_RF, (ccy,)).fetchall()

        data = [(True, rate)]
        if ccy in self._rf:
            old_rate = self._rf[ccy]
            warnings.warn('The rate {} is set as current risk free and will be overridden'
                          .format(old_rate))
            data.append((False, old_rate))

        self._db.executemany(self._Q_SET_RF, data, commit=True)


def get_rf_glob() -> RateFactory:
    """ Returns the pointer to the global RateFactory """
    return RateFactory()
