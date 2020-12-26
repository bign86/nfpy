#
# Market Assets Data Base Model
# Base class for market models
#

import numpy as np
import pandas as pd
from typing import Union

from nfpy.Assets import get_af_glob
from nfpy.Calendar import get_calendar_glob
import nfpy.Math as Mat
from nfpy.Tools import (Constants as Cn, Utilities as Ut)
import nfpy.Trading.Signals as Sig


class BaseMADMResult(Ut.AttributizedDict):
    """ Base object containing the results of the market asset models. """


class MarketAssetsDataBaseModel(object):
    """ Market Assets Data Base Model class """

    _RES_OBJ = BaseMADMResult

    def __init__(self, uid: str, date: Union[str, pd.Timestamp] = None,
                 date_fmt: str = '%Y-%m-%d', **kwargs):
        # Handlers
        self._cal = get_calendar_glob()
        self._af = get_af_glob()

        # Input data objects
        self._uid = uid
        self._asset = self._af.get(uid)
        if date is None:
            self._t0 = self._cal.t0
        elif isinstance(date, str):
            self._t0 = pd.to_datetime(date, format=date_fmt)

        # Working data
        self._dt = {}
        self._time_spans = (Cn.DAYS_IN_1M, 3*Cn.DAYS_IN_1M, 6*Cn.DAYS_IN_1M,
                            Cn.DAYS_IN_1Y, 3*Cn.DAYS_IN_1Y)
        self._is_calculated = False

    def _res_update(self, **kwargs):
        self._dt.update(kwargs)

    def _calculate(self):
        asset, t0 = self._asset, self._t0

        # Price results
        prices = asset.prices
        v = prices.values
        dt = prices.index.values
        last_price, idx = Mat.last_valid_value(v, dt, t0.asm8)
        last_p_date = prices.index[idx]

        # Variances
        length = len(self._time_spans)
        stats = np.empty((3, length))
        for i in range(length):
            n = self._time_spans[i]
            start = self._cal.shift(t0, n, 'D', fwd=False)
            stats[0, i] = asset.return_volatility(start, t0)
            mean_ret = asset.expct_return(start, t0)
            stats[1, i] = Mat.compound(mean_ret, Cn.BDAYS_IN_1Y / n)
            total_ret = asset.total_return(start, t0)
            stats[2, i] = Mat.compound(total_ret, Cn.BDAYS_IN_1Y / n)

        # Moving averages
        ma_fast = Sig.ewma(prices, w=21)
        ma_slow = Sig.ewma(prices, w=120)

        # Record results
        calc = ['volatility', 'mean return', 'tot. return']
        self._res_update(stats=pd.DataFrame(stats, index=calc,
                         columns=self._time_spans), date=t0, prices=prices,
                         last_price=last_price, last_price_date=last_p_date,
                         uid=self._uid, ma_fast=ma_fast, ma_slow=ma_slow)

    def _create_output(self):
        res = self._RES_OBJ()
        for k, v in self._dt.items():
            setattr(res, k, v)
        return res

    def result(self, **kwargs):
        if not self._is_calculated:
            self._calculate()
            self._is_calculated = True

        return self._create_output()


def MADModel(uid: str, date: Union[str, pd.Timestamp] = None,
             date_fmt: str = '%Y-%m-%d') -> BaseMADMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return MarketAssetsDataBaseModel(uid, date, date_fmt).result()
