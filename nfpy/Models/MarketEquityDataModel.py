#
# Market Equity Data Base Model
# Class for equity market models
#

import numpy as np
import pandas as pd
from typing import Optional

from nfpy.Calendar import TyDate
import nfpy.Math as Math
from nfpy.Tools import (Constants as Cn)

from .MarketAssetsDataBaseModel import (MADMResult, MarketAssetsDataBaseModel)


class MEDMResult(MADMResult):
    """ Base object containing the results of the market asset models. """


class MarketEquityDataModel(MarketAssetsDataBaseModel):
    """ Market Equity Data Base Model class """

    _RES_OBJ = MEDMResult

    def __init__(self, uid: str, date: Optional[TyDate] = None, **kwargs):
        super().__init__(uid, date, **kwargs)
        self._index = self._af.get(self._asset.index)

    def _calculate(self) -> None:
        super()._calculate()

        # Performance
        self._calc_performance()

    def _calc_price_res(self) -> None:
        asset, index = self._asset, self._index
        t0 = self._t0

        prices = asset.prices
        returns = asset.returns
        v = prices.values
        dt = prices.index.values
        last_price, idx = Math.last_valid_value(v, dt, t0.asm8)
        last_p_date = prices.index[idx]

        self._res_update(prices=prices, last_price=last_price,
                         last_price_date=last_p_date, returns=returns,
                         index_returns=index.returns)

    def _calc_statistics(self) -> None:
        asset, index = self._asset, self._index
        t0 = self._t0
        length = len(self._time_spans)

        stats = np.empty((8, length))
        betas = []

        v, dt = asset.prices.values, asset.prices.index.values
        last_price = self._dt['last_price']
        last_price_date = self._dt['last_price_date']

        for i in range(length):
            start = self._cal.shift(t0, -self._time_spans[i], 'D')
            real_n = self._cal.run_len(start, last_price_date)
            stats[0, i] = asset.return_volatility(start, t0)

            mean_ret = asset.expct_return(start, t0)
            stats[1, i] = Math.compound(mean_ret, Cn.BDAYS_IN_1Y / real_n)

            # From timing results this solution (combined with obtaining p_t0
            # above) is between 1.5 and 3.1 times faster than using
            # Asset.total_return()
            p_start = Math.next_valid_value(v, dt, start.asm8)[0]
            total_ret = last_price / p_start - 1.
            stats[2, i] = Math.compound(total_ret, Cn.BDAYS_IN_1Y / real_n)

            returns = asset.returns
            beta_results = Math.beta(
                returns.index.values,
                returns.values,
                index.returns.values,
                start=start.asm8,
                end=t0.asm8
            )
            betas.append(beta_results[1:])
            stats[3:5, i] = beta_results[1:3]

            stats[5, i] = asset.correlation(start=start, end=t0)[0, 1]

            mean_index_ret = index.expct_return(start, t0)
            rt, delta = Math.sml(mean_ret, beta_results[1], .0, mean_index_ret)
            stats[6, i] = Math.compound(rt, Cn.BDAYS_IN_1Y / real_n)
            stats[7, i] = Math.compound(delta, Cn.BDAYS_IN_1Y / real_n)

        self._res_update(
            stats=pd.DataFrame(
                stats,
                index=(
                    'volatility', 'mean return', 'tot. return', 'beta',
                    'adj. beta', 'correlation', 'SML ret', 'delta pricing'
                ),
                columns=self._time_spans
            ),
            beta_params=betas[3]
        )

    def _calc_performance(self) -> None:
        t0 = self._t0
        start = self._cal.shift(t0, -2 * Cn.DAYS_IN_1Y, 'D')

        self._res_update(
            perf=self._asset.performance(start=start, end=t0),
            perf_idx=self._index.performance(start=start, end=t0)
        )


def MEDModel(uid: str, date: Optional[TyDate] = None) -> MEDMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return MarketEquityDataModel(uid, date).result()
