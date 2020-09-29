#
# Rate factory class
# Class to handle rate and curves
#

import warnings

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
    _Q_GET_RF = """select r.uid from Rate as r join CurveConstituents as cc
on r.uid = cc.bucket join Curve as c on c.uid = cc.uid
where c.currency = ? and r.is_rf = True;"""
    _Q_SET_RF = """update Rate set is_rf = ? where uid = ?;"""

    def __init__(self):
        self._db = get_db_glob()
        self._qb = get_qb_glob()
        self._af = get_af_glob()

    def get_rf(self, ccy: str) -> Rate:
        res = self._db.execute(self._Q_GET_RF, (ccy,)).fetchall()
        if not res:
            raise MissingData('No risk free found for {}'.format(ccy))
        if len(res) > 1:
            raise ValueError('More than one risk free found for {}'.format(ccy))
        return self._af.get(res[0][0])

    def set_rf(self, ccy: str, rate: str):
        """ Set a risk free rate. """
        res = self._db.execute(self._Q_GET_RF, (ccy,)).fetchall()

        if len(res) > 0:
            old_rate = res[0][0]
            warnings.warn('The rate {} is set as current risk free and will be overridden'
                          .format(old_rate))
            self._db.execute(self._Q_SET_RF, (False, old_rate), commit=True)
        else:
            self._db.execute(self._Q_SET_RF, (True, rate), commit=True)


def get_rf_glob() -> RateFactory:
    """ Returns the pointer to the global RateFactory """
    return RateFactory()
