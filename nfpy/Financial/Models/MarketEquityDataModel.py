#
# Market Equity Data Base Model
# Class for equity market models
#

import numpy as np
import pandas as pd
from typing import Union

import nfpy.Math as Mat
from nfpy.Tools import (Constants as Cn)

from .MarketAssetsDataBaseModel import (BaseMADMResult,
                                        MarketAssetsDataBaseModel)


class MEDMResult(BaseMADMResult):
    """ Base object containing the results of the market asset models. """


class MarketEquityDataModel(MarketAssetsDataBaseModel):
    """ Market Equity Data Base Model class """

    _RES_OBJ = MEDMResult

    def __init__(self, uid: str, date: Union[str, pd.Timestamp] = None,
                 w_ma_slow: int = 120, w_ma_fast: int = 21, sr_mult: float = 5.,
                 date_fmt: str = '%Y-%m-%d', **kwargs):
        super().__init__(uid, date, w_ma_slow, w_ma_fast, sr_mult,
                         date_fmt, **kwargs)
        self._index = self._af.get(self._asset.index)

    def _calculate(self):
        super()._calculate()

        # Performance
        self._calc_performance()

    def _calc_price_res(self):
        asset, index = self._asset, self._index
        t0 = self._t0

        prices = asset.prices
        returns = asset.returns
        v = prices.values
        dt = prices.index.values
        last_price, idx = Mat.last_valid_value(v, dt, t0.asm8)
        last_p_date = prices.index[idx]

        self._res_update(prices=prices, last_price=last_price,
                         last_price_date=last_p_date, returns=returns,
                         index_returns=index.returns)

    def _calc_statistics(self):
        asset, index = self._asset, self._index
        t0 = self._t0
        length = len(self._time_spans)

        stats = np.empty((8, length))
        betas = []
        for i in range(length):
            n = self._time_spans[i]
            start = self._cal.shift(t0, n, 'D', fwd=False)
            stats[0, i] = asset.return_volatility(start, t0)
            mean_ret = asset.expct_return(start, t0)
            stats[1, i] = Mat.compound(mean_ret, Cn.BDAYS_IN_1Y / n)
            total_ret = asset.total_return(start, t0)
            stats[2, i] = Mat.compound(total_ret, Cn.BDAYS_IN_1Y / n)
            beta_results = asset.beta(start=start, end=t0)
            betas.append(beta_results[1:])
            stats[3:5, i] = beta_results[1:3]
            stats[5, i] = asset.correlation(start=start, end=t0)[1][0, 1]
            mean_index_ret = index.expct_return(start, t0)
            rt, delta = Mat.sml(mean_ret, beta_results[1], .0, mean_index_ret)
            stats[6, i] = Mat.compound(rt, Cn.BDAYS_IN_1Y / n)
            stats[7, i] = Mat.compound(delta, Cn.BDAYS_IN_1Y / n)

        calc = ['volatility', 'mean return', 'tot. return', 'beta',
                'adj. beta', 'correlation', 'SML ret', 'delta pricing']
        self._res_update(stats=pd.DataFrame(stats, index=calc,
                                            columns=self._time_spans),
                         beta_params=betas[3])

    def _calc_performance(self):
        asset, index = self._asset, self._index
        t0 = self._t0

        start = self._cal.shift(t0, 2*Cn.BDAYS_IN_1Y, 'D', fwd=False)
        perf = asset.performance(start=start, end=t0)
        perf_idx = index.performance(start=start, end=t0)

        self._res_update(perf=perf, perf_idx=perf_idx)


def MEDModel(uid: str, date: Union[str, pd.Timestamp] = None,
             w_ma_slow: int = 120, w_ma_fast: int = 21, sr_mult: float = 5.,
             date_fmt: str = '%Y-%m-%d') -> MEDMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return MarketEquityDataModel(uid, date, w_ma_slow, w_ma_fast, sr_mult,
                                 date_fmt).result()
