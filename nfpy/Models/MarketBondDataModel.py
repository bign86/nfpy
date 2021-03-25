#
# Market Bond Data Base Model
# Class for equity market models
#

import numpy as np
import pandas as pd
from typing import Union

import nfpy.Financial as Fin
from nfpy.Tools import (Constants as Cn)

from .MarketAssetsDataBaseModel import (BaseMADMResult,
                                        MarketAssetsDataBaseModel)


class MBDMResult(BaseMADMResult):
    """ Base object containing the results of the market asset models. """


class MarketBondDataModel(MarketAssetsDataBaseModel):
    """ Market Equity Data Base Model class """

    _RES_OBJ = MBDMResult

    def _calculate(self):
        super()._calculate()
        self._calc_bond_math()

    def _calc_bond_math(self):
        asset, t0 = self._asset, self._t0
        p = asset.prices
        last_price = self._dt['last_price']
        last_p_date = self._dt['last_price_date'].asm8

        # Calculate volatility
        m1, m6 = Cn.BDAYS_IN_1M, Cn.BDAYS_IN_1M * 6
        p_vola_1m = p.iloc[-m1:].std() * np.sqrt(m1)
        p_vola_6m = p.iloc[-m6:].std() * np.sqrt(m6)

        # Yield across time
        dt = self._cal.calendar
        ytm = asset.ytm(dt)
        last_ytm, _ = Fin.last_valid_value(ytm.values, dt.values, last_p_date)

        # Yield vs Price plot
        dates = np.array([last_p_date] * 11)
        prices = np.zeros(11) + last_price
        prices[:7] *= np.arange(.94, 1.061, .02)
        prices[7] += p_vola_1m
        prices[8] -= p_vola_1m
        prices[9] += p_vola_6m
        prices[10] -= p_vola_6m
        arr_ytm, _ = Fin.calc_ytm(dates, asset.inception_date.asm8,
                                  asset.maturity.asm8, prices,
                                  asset.cf['value'].values,
                                  asset.cf.index.values,
                                  asset.cf['dtype'].values, .0)

        arr_ytm = np.vstack((prices, arr_ytm))

        # Fair value calculation
        rates = np.zeros(4)
        rates[1:] = np.arange(-.01, .011, .01) + last_ytm

        arr_fv, _ = Fin.calc_fv(t0.asm8, asset.inception_date.asm8,
                                asset.maturity.asm8, .0,
                                asset.cf['value'].values, asset.cf.index.values,
                                asset.cf['dtype'].values, rates)
        arr_fv_delta = (arr_fv / last_price) - 1.
        arr_fv = np.vstack((arr_fv, arr_fv_delta))

        # Fair values and discounted cash flows
        arr_dcf, cf_dt = Fin.calc_dcf(t0.asm8, asset.inception_date.asm8,
                                      asset.maturity.asm8,
                                      asset.cf['value'].values,
                                      asset.cf.index.values,
                                      asset.cf['dtype'].values,
                                      rates)

        # Group cash flows
        arr_sum, cf_dt_unique = Fin.aggregate_cf(arr_dcf, cf_dt)
        cf_dt_unique = [pd.to_datetime(t).strftime('%Y-%m-%d')
                        for t in cf_dt_unique]

        arr_cf = np.hstack((arr_fv.T, arr_sum))
        cols = ['Fv', '%diff'] + cf_dt_unique
        fair_values = pd.DataFrame(arr_cf, index=rates, columns=cols)

        # Convexity and duration
        dur = asset.duration(t0)
        cvx = asset.convexity(t0)

        # Record results
        self._res_update(yields=ytm, yields_array=arr_ytm[:, :7],
                         ytm_bars=arr_ytm[:, 7:], last_ytm=last_ytm,
                         fair_values=fair_values, convexity=cvx,
                         duration=dur)


def MBDModel(uid: str, date: Union[str, pd.Timestamp] = None) -> MBDMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return MarketBondDataModel(uid, date).result()
