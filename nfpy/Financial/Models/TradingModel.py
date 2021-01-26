#
# Trading Model
# Base class for trading
#

import pandas as pd
from typing import Union

from nfpy.Assets import get_af_glob
from nfpy.Calendar import get_calendar_glob
from nfpy.Tools import (Constants as Cn, Utilities as Ut)
import nfpy.Trading.Signals as Sig
import nfpy.Trading.Trends as Tr


class TradingResult(Ut.AttributizedDict):
    """ Base object containing the results of the trading models. """


class TradingModel(object):
    """ Trading Model class """

    _RES_OBJ = TradingResult

    def __init__(self, uid: str, date: Union[str, pd.Timestamp] = None,
                 w_ma_slow: int = 120, w_ma_fast: int = 21,
                 sr_mult: float = 5., **kwargs):
        # Handlers
        self._cal = get_calendar_glob()
        self._af = get_af_glob()

        # Input data objects
        self._uid = uid
        self._asset = self._af.get(uid)
        if date is None:
            self._t0 = self._cal.t0
        elif isinstance(date, str):
            self._t0 = pd.to_datetime(date, format='%Y-%m-%d')
        else:
            self._t0 = date
        self._w_ma_slow = w_ma_slow
        self._w_ma_fast = w_ma_fast
        self._sr_mult = sr_mult

        # Working data
        self._dt = {}
        self._time_spans = (Cn.DAYS_IN_1M, 3 * Cn.DAYS_IN_1M, 6 * Cn.DAYS_IN_1M,
                            Cn.DAYS_IN_1Y, 3 * Cn.DAYS_IN_1Y)
        self._is_calculated = False

        self._res_update(date=self._t0, uid=self._uid, w_slow=self._w_ma_slow,
                         w_fast=self._w_ma_fast, prices=self._asset.prices)

    def _res_update(self, **kwargs):
        self._dt.update(kwargs)

    def _calculate(self):
        # Support/Resistances
        self._calc_sr()

        # Moving averages
        self._calc_wma()

    def _calc_sr(self):
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

        self._res_update(sr_fast=sr_fast, sr_slow=sr_slow)

    def _calc_wma(self):
        prices = self._asset.prices
        w_fast, w_slow = self._w_ma_fast, self._w_ma_slow

        # Moving averages
        wma_fast = Sig.ewma(prices, w=w_fast)
        wma_slow = Sig.ewma(prices, w=w_slow)

        self._res_update(ma_fast=wma_fast, ma_slow=wma_slow)

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


def TRDModel(uid: str, date: Union[str, pd.Timestamp] = None,
             w_ma_slow: int = 120, w_ma_fast: int = 21, sr_mult: float = 5.,
             ) -> TradingResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return TradingModel(uid, date, w_ma_slow, w_ma_fast, sr_mult).result()
