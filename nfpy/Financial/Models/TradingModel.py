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
import nfpy.Trading.Trends as Tr


class BaseMADMResult(Ut.AttributizedDict):
    """ Base object containing the results of the market asset models. """


class MarketAssetsDataBaseModel(object):
    """ Market Assets Data Base Model class """

    _RES_OBJ = BaseMADMResult

    def __init__(self, uid: str, date: Union[str, pd.Timestamp] = None,
                 w_ma_slow: int = 120, w_ma_fast: int = 21, sr_mult: float = 5.,
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
        self._w_ma_slow = w_ma_slow
        self._w_ma_fast = w_ma_fast
        self._sr_mult = sr_mult

        # Working data
        self._dt = {}
        self._time_spans = (Cn.DAYS_IN_1M, 3 * Cn.DAYS_IN_1M, 6 * Cn.DAYS_IN_1M,
                            Cn.DAYS_IN_1Y, 3 * Cn.DAYS_IN_1Y)
        self._is_calculated = False

        self._res_update(date=self._t0, uid=self._uid, w_slow=self._w_ma_slow,
                         w_fast=self._w_ma_fast)

    def _res_update(self, **kwargs):
        self._dt.update(kwargs)

    def _calculate(self):
        # Price results
        self._calc_price_res()

        # Time-dependent statistics
        self._calc_statistics()

        # Trading quantities
        self._calc_trading()

    def _calc_price_res(self):
        asset, t0 = self._asset, self._t0

        prices = asset.prices
        v = prices.values
        dt = prices.index.values
        last_price, idx = Mat.last_valid_value(v, dt, t0.asm8)
        last_p_date = prices.index[idx]

        self._res_update(prices=prices, last_price=last_price,
                         last_price_date=last_p_date)

    def _calc_statistics(self):
        asset, t0 = self._asset, self._t0
        length = len(self._time_spans)

        stats = np.empty((3, length))

        v, dt = asset.prices.values, asset.prices.index.values
        last_price = self._dt['last_price']
        last_price_date = self._dt['last_price_date']

        for i in range(length):
            n = self._time_spans[i]
            start = self._cal.shift(t0, -n, 'D')
            real_n = self._cal.run_len(start, last_price_date)
            stats[0, i] = asset.return_volatility(start, t0)

            mean_ret = asset.expct_return(start, t0)
            stats[1, i] = Mat.compound(mean_ret, Cn.BDAYS_IN_1Y / real_n)

            # From timing results this solution (combined with obtaining p_t0
            # above) is between 1.5 and 3.1 times faster than using
            # Asset.total_return()
            p_start = Mat.next_valid_value(v, dt, start.asm8)[0]
            total_ret = last_price / p_start - 1.
            stats[2, i] = Mat.compound(total_ret, Cn.BDAYS_IN_1Y / real_n)

        calc = ['volatility', 'mean return', 'tot. return']
        self._res_update(stats=pd.DataFrame(stats, index=calc,
                                            columns=self._time_spans))

    def _calc_trading(self):
        prices = self._asset.prices
        w_fast, w_slow = self._w_ma_fast, self._w_ma_slow

        # Support/resistances
        p_slow = prices.iloc[-int(w_slow * self._sr_mult):]
        _, _, max_i, min_i = Tr.find_ts_extrema(p_slow, w=w_slow)
        all_i = sorted(max_i + min_i)
        pp = p_slow.iloc[all_i]
        sr_slow = Tr.group_extrema(pp, dump=.75)[0]

        p_fast = prices.iloc[-int(w_fast * self._sr_mult):]
        _, _, max_i, min_i = Tr.find_ts_extrema(p_fast, w=w_fast)
        all_i = sorted(max_i + min_i)
        pp = p_fast.iloc[all_i]
        sr_fast = Tr.group_extrema(pp, dump=.75)[0]

        # Record results
        self._res_update(w_fast=w_fast, sr_fast=sr_fast,
                         w_slow=w_slow, sr_slow=sr_slow)

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
             w_ma_slow: int = 120, w_ma_fast: int = 21, sr_mult: float = 5.,
             date_fmt: str = '%Y-%m-%d') -> BaseMADMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return MarketAssetsDataBaseModel(uid, date, w_ma_slow, w_ma_fast, sr_mult,
                                     date_fmt).result()
