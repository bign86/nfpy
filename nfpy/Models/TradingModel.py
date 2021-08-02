#
# Trading Model
# Base class for trading
#

from datetime import timedelta
import pandas as pd
import numpy as np
from typing import Union

import nfpy.Calendar as Cal
import nfpy.Financial.Math as Math
from nfpy.Trading import (Indicators as Ind, Strategies as Str)
import nfpy.Trading as Trd

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
        self._cal = Cal.get_calendar_glob()

        self._w_ma_slow = w_ma_slow
        self._w_ma_fast = w_ma_fast
        self._sr_mult = sr_mult

        self._res_update(date=self._t0, uid=self._uid, sr_mult=self._sr_mult,
                         w_slow=self._w_ma_slow, w_fast=self._w_ma_fast,
                         prices=self._asset.prices)

    def _calculate(self):
        # Support/Resistances
        self._calc_alerts()

        # Moving averages
        self._calc_wma()

    def _calc_alerts(self):
        ae = Trd.AlertsEngine()
        window = Cal.today(mode='datetime') - timedelta(days=10)
        ae.raise_alerts(self._uid, date_checked=window)
        self._res_update(
            alerts=ae.fetch(
                self._uid,
                triggered=True,
                date_triggered=window
            )
        )

    def _calc_wma(self):
        prices, t0 = self._asset.prices, self._t0
        w_fast, w_slow = self._w_ma_fast, self._w_ma_slow
        sr_mult = self._sr_mult

        # Moving averages
        p_slow = prices.iloc[-int(w_slow * (sr_mult + 1)):]
        # wma_slow = pd.Series(
        #    Ind.ewma(p_slow.values, w=w_slow),
        #    p_slow.index.values
        # )

        fast_length = int(w_fast * (sr_mult + 1))
        p_fast = prices.iloc[-fast_length:]
        signals, ma = Str.TwoEMACross(w_fast, w_slow, True) \
            .__call__(p_fast.index.values, p_fast.values)
        # wma_fast = pd.Series(ma[w_fast], p_fast.index.values)

        if len(signals.signals) > 0:
            last_price = Math.last_valid_value(
                p_fast.values,
                p_fast.index.values,
                t0.asm8
            )[0]

            sig_price = p_fast.iloc[signals.indices].values
            res = np.empty(sig_price.shape)
            res[:-1] = sig_price[1:] / sig_price[:-1] - 1.
            res[-1] = last_price / sig_price[-1] - 1.

            df = pd.DataFrame(
                index=signals.dates,
                columns=['signal', 'price', 'return', 'delta days']
            )
            df['signal'] = signals.signals
            df['price'] = sig_price
            df['return'] = res
            df['delta days'] = (t0 - df.index).days

        else:
            df = pd.DataFrame(columns=['signal', 'price', 'return', 'delta days'])

        df.replace(to_replace={'signal': {1: 'buy', -1: 'sell'}}, inplace=True)
        self._res_update(
            ma_fast=pd.Series(
                ma[w_fast],
                p_fast.index.values
            ),
            ma_slow=pd.Series(
                Ind.ewma(p_slow.values, w=w_slow),
                p_slow.index.values
            ),
            signals=df
        )

    def _otf_calculate(self, **kwargs) -> dict:
        pass

    def _check_applicability(self):
        pass


def TRDModel(uid: str, date: Union[str, pd.Timestamp] = None,
             w_ma_slow: int = 120, w_ma_fast: int = 21, sr_mult: float = 5.,
             ) -> TradingResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return TradingModel(uid, date, w_ma_slow, w_ma_fast, sr_mult).result()
