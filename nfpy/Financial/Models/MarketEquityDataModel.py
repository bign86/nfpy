#
# Market Equity Data Base Model
# Class for equity market models
#

import numpy as np
import pandas as pd
from typing import Union

import nfpy.Math as Mat
from nfpy.Tools import (Constants as Cn)
import nfpy.Trading.Signals as Sig

from .MarketAssetsDataBaseModel import (BaseMADMResult,
                                        MarketAssetsDataBaseModel)


class MEDMResult(BaseMADMResult):
    """ Base object containing the results of the market asset models. """


class MarketEquityDataModel(MarketAssetsDataBaseModel):
    """ Market Equity Data Base Model class """

    _RES_OBJ = MEDMResult

    def __init__(self, uid: str, date: Union[str, pd.Timestamp] = None,
                 date_fmt: str = '%Y-%m-%d', **kwargs):
        super().__init__(uid, date, date_fmt, **kwargs)
        self._index = self._af.get(self._asset.index)

    def _calculate(self):
        asset = self._asset
        index = self._index
        t0 = self._t0

        # Asset prices and returns
        prices = asset.prices
        returns = asset.returns
        idx = Mat.last_valid_index(prices.values)
        last_price = prices.values[idx]
        last_p_date = prices.index[idx]

        # Variances
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
            # stats[4, i] = beta_results[2]
            stats[5, i] = asset.correlation(start=start, end=t0)[1][0, 1]
            mean_index_ret = index.expct_return(start, t0)
            rt, delta = Mat.sml(mean_ret, beta_results[1], .0, mean_index_ret)
            stats[6, i] = Mat.compound(rt, Cn.BDAYS_IN_1Y / n)
            stats[7, i] = Mat.compound(delta, Cn.BDAYS_IN_1Y / n)

        # Moving averages
        ma_fast = Sig.ewma(prices, w=21)
        ma_slow = Sig.ewma(prices, w=120)

        # Record results
        calc = ['volatility', 'mean return', 'tot. return', 'beta',
                'adj. beta', 'correlation', 'SML ret', 'delta pricing']
        self._res_update(stats=pd.DataFrame(stats, index=calc, columns=self._time_spans),
                         date=t0, prices=prices, last_price=last_price,
                         last_price_date=last_p_date, uid=self._uid,
                         returns=returns, index_returns=index.returns,
                         beta_params=betas[3], ma_fast=ma_fast, ma_slow=ma_slow)


def MEDModel(uid: str, date: Union[str, pd.Timestamp] = None,
             date_fmt: str = '%Y-%m-%d') -> MEDMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return MarketEquityDataModel(uid, date, date_fmt).result()
