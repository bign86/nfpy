#
# Market Assets Data Base Model
# Base class for market models
#

import numpy as np
import pandas as pd
from typing import Union

import nfpy.Math as Math
from nfpy.Tools import Constants as Cn

from .BaseModel import (BaseModel, BaseModelResult)


class MADMResult(BaseModelResult):
    """ Base object containing the results of the market asset models. """


class MarketAssetsDataBaseModel(BaseModel):
    """ Market Assets Data Base Model class """

    _RES_OBJ = MADMResult

    def __init__(self, uid: str, date: Union[str, pd.Timestamp] = None,
                 **kwargs):
        """
        Inputs:
            uid [str]: uid of the asset
            FIXME: put types
            date [???]: reference date for the calculation (Default calendar.t0)
            kwargs:
                - time_spans [tuple[int]]: windows to calculate the statistics
                    on (Default: (1M, 3M, 6M, 1Y, 3Y))
        """
        super().__init__(uid, date)

        self._time_spans = kwargs.get('time_spans', None)
        if not self._time_spans:
            self._time_spans = (
                Cn.DAYS_IN_1M, 3 * Cn.DAYS_IN_1M, 6 * Cn.DAYS_IN_1M,
                Cn.DAYS_IN_1Y, 3 * Cn.DAYS_IN_1Y
            )

        self._res_update(date=self._t0, uid=self._uid)

    def _calculate(self):
        # Price results
        self._calc_price_res()

        # Time-dependent statistics
        self._calc_statistics()

    def _calc_price_res(self):
        prices = self._asset.prices
        last_price, idx = Math.last_valid_value(
            prices.values,
            prices.index.values,
            self._t0.asm8
        )

        self._res_update(prices=prices, last_price=last_price,
                         last_price_date=prices.index[idx])

    def _calc_statistics(self):
        asset, t0 = self._asset, self._t0
        length = len(self._time_spans)

        stats = np.empty((3, length))

        v, dt = asset.prices.values, asset.prices.index.values
        last_price = self._dt['last_price']
        last_price_date = self._dt['last_price_date']

        for i in range(length):
            start = self._cal.shift(t0, -self._time_spans[i], 'D')
            real_n = self._cal.run_len(start, last_price_date)
            stats[0, i] = asset.return_volatility(start, t0)

            stats[1, i] = Math.compound(
                asset.expct_return(start, t0),
                Cn.BDAYS_IN_1Y / real_n
            )

            # From timing results this solution (combined with obtaining p_t0
            # above) is between 1.5 and 3.1 times faster than using
            # Asset.total_return()
            p_start = Math.next_valid_value(v, dt, start.asm8)[0]
            stats[2, i] = Math.compound(
                last_price / p_start - 1.,
                Cn.BDAYS_IN_1Y / real_n
            )

        self._res_update(
            stats=pd.DataFrame(
                stats,
                index=('volatility', 'mean return', 'tot. return'),
                columns=self._time_spans
            )
        )

    def _otf_calculate(self, **kwargs) -> dict:
        return kwargs

    def _check_applicability(self):
        pass


def MADModel(uid: str, date: Union[str, pd.Timestamp] = None) -> MADMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return MarketAssetsDataBaseModel(uid, date).result()
