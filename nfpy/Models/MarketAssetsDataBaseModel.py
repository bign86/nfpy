#
# Market Assets Data Base Model
# Base class for market models
#

import numpy as np
import pandas as pd
from typing import Union

from nfpy.Calendar import get_calendar_glob
import nfpy.Financial.Math as Math
from nfpy.Tools import Constants as Cn

from .BaseModel import (BaseModel, BaseModelResult)


class BaseMADMResult(BaseModelResult):
    """ Base object containing the results of the market asset models. """


class MarketAssetsDataBaseModel(BaseModel):
    """ Market Assets Data Base Model class """

    _RES_OBJ = BaseMADMResult

    def __init__(self, uid: str, date: Union[str, pd.Timestamp] = None,
                 **kwargs):
        super().__init__(uid, date)

        self._cal = get_calendar_glob()
        self._time_spans = (Cn.DAYS_IN_1M, 3 * Cn.DAYS_IN_1M, 6 * Cn.DAYS_IN_1M,
                            Cn.DAYS_IN_1Y, 3 * Cn.DAYS_IN_1Y)

        self._res_update(date=self._t0, uid=self._uid)

    def _calculate(self):
        # Price results
        self._calc_price_res()

        # Time-dependent statistics
        self._calc_statistics()

    def _calc_price_res(self):
        asset, t0 = self._asset, self._t0

        prices = asset.prices
        v = prices.values
        dt = prices.index.values
        last_price, idx = Math.last_valid_value(v, dt, t0.asm8)
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
            stats[1, i] = Math.compound(mean_ret, Cn.BDAYS_IN_1Y / real_n)

            # From timing results this solution (combined with obtaining p_t0
            # above) is between 1.5 and 3.1 times faster than using
            # Asset.total_return()
            p_start = Math.next_valid_value_date(v, dt, start.asm8)[0]
            total_ret = last_price / p_start - 1.
            stats[2, i] = Math.compound(total_ret, Cn.BDAYS_IN_1Y / real_n)

        calc = ['volatility', 'mean return', 'tot. return']
        self._res_update(stats=pd.DataFrame(stats, index=calc,
                                            columns=self._time_spans))

    def _otf_calculate(self, **kwargs) -> dict:
        return kwargs

    def _check_applicability(self):
        pass


def MADModel(uid: str, date: Union[str, pd.Timestamp] = None,
             ) -> BaseMADMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return MarketAssetsDataBaseModel(uid, date).result()
