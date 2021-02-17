#
# Trading Model
# Base class for trading
#

import pandas as pd
import numpy as np
from typing import Union

from nfpy.Calendar import get_calendar_glob
import nfpy.Math as Mat
from nfpy.Trading import (Signals as Sig, Strategies as Str, Trends as Tr)

from .BaseModel import (BaseModel, BaseModelResult)


class TradingResult(BaseModelResult):
    """ Base object containing the results of the trading models. """


class TradingModel(BaseModel):
    """ Trading Model class. """

    _RES_OBJ = TradingResult

    def __init__(self, uid: str, date: Union[str, pd.Timestamp] = None,
                 w_ma_slow: int = 120, w_ma_fast: int = 21,
                 sr_mult: float = 5., **kwargs):
        super().__init__(uid, date)

        self._cal = get_calendar_glob()

        self._w_ma_slow = w_ma_slow
        self._w_ma_fast = w_ma_fast
        self._sr_mult = sr_mult

        self._res_update(date=self._t0, uid=self._uid, sr_mult=self._sr_mult,
                         w_slow=self._w_ma_slow, w_fast=self._w_ma_fast,
                         prices=self._asset.prices)

    def _calculate(self):
        # Support/Resistances
        self._calc_sr()

        # Moving averages
        self._calc_wma()

    def _calc_sr(self):
        prices = self._asset.prices
        w_fast, w_slow = self._w_ma_fast, self._w_ma_slow
        sr_mult = self._sr_mult

        # Support/resistances
        n_back_slow = -int(w_slow * sr_mult)
        p_slow = prices.iloc[n_back_slow:]
        max_i, min_i = Tr.find_ts_extrema(p_slow, w=w_slow)
        all_i = sorted(max_i + min_i)
        pp = p_slow.iloc[all_i]
        sr_slow = Tr.group_extrema(pp, dump=.75)[0]

        n_back_fast = -int(w_fast * sr_mult)
        p_fast = prices.iloc[n_back_fast:]
        max_i, min_i = Tr.find_ts_extrema(p_fast, w=w_fast)
        all_i = sorted(max_i + min_i)
        pp = p_fast.iloc[all_i]
        sr_fast = Tr.group_extrema(pp, dump=.75)[0]

        start_date = prices.index[n_back_fast]
        vola = self._asset.return_volatility(start=start_date)
        v_sr_slow, v_sr_fast = Tr.merge_rs(abs(vola),
                                           (sr_slow, sr_fast))

        self._res_update(sr_fast=v_sr_fast, sr_slow=v_sr_slow)

    def _calc_wma(self):
        prices, t0 = self._asset.prices, self._t0
        w_fast, w_slow = self._w_ma_fast, self._w_ma_slow
        sr_mult = self._sr_mult

        # Moving averages
        p_slow = prices.iloc[-int(w_slow * (sr_mult + 1)):]
        wma_slow = Sig.ewma(p_slow, w=w_slow)

        fast_length = int(w_fast * (sr_mult + 1))
        p_fast = prices.iloc[-fast_length:]
        signals, wma_fast, _ = Str.two_ema_cross(p_fast, w_fast, w_slow,
                                                 slow_ma=wma_slow)

        df = pd.DataFrame(columns=['signal', 'price', 'return', 'delta days'])
        if len(signals) > 0:
            p, dt = p_fast.values, p_fast.index.values
            last_price = Mat.last_valid_value(p, dt, t0.asm8)[0]

            sig_price = p_fast.loc[signals.index]
            sig_price = sig_price.values
            res = np.empty(sig_price.shape)
            res[:-1] = sig_price[1:] / sig_price[:-1] - 1.
            res[-1] = last_price / sig_price[-1] - 1.

            df['signal'] = signals
            df['price'] = sig_price
            df['return'] = res
            df['delta days'] = (t0 - df.index).days

        df.replace(to_replace={'signal': {1: 'buy', -1: 'sell'}}, inplace=True)

        self._res_update(ma_fast=wma_fast, ma_slow=wma_slow, signals=df)

    def _otf_calculate(self, **kwargs) -> dict:
        pass

    def _check_applicability(self):
        pass


def TRDModel(uid: str, date: Union[str, pd.Timestamp] = None,
             w_ma_slow: int = 120, w_ma_fast: int = 21, sr_mult: float = 5.,
             ) -> TradingResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return TradingModel(uid, date, w_ma_slow, w_ma_fast, sr_mult).result()
