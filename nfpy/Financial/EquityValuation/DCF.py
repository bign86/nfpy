#
# Discounted Cash Flow Model
# Class to calculate a stock fair value using the DCF model
#

import numpy as np
import pandas as pd
import pandas.tseries.offsets as off
from typing import Any

import nfpy.Financial as Fin
import nfpy.Math as Math

from .BaseFundamentalModel import (BaseFundamentalModel, FundamentalModelResult)
from .BuildingBlocks import CAPM


class DCFResult(FundamentalModelResult):
    """ Object containing the results of the Discounted Cash Flow Model. """

    @property
    def fcf(self) -> pd.Series:
        return self.df['fcf']

    @property
    def cfo(self) -> pd.Series:
        return self.df['cfo']

    @property
    def capex(self) -> pd.Series:
        return self.df['capex']

    @property
    def tax_rate(self) -> pd.Series:
        return self.df['tax_rate']


class DCF(BaseFundamentalModel):
    """ Discounted Cash Flow Model class. """

    _RES_OBJ = DCFResult
    _COLS_FCF = [
        'fcf', 'calc_fcf', 'revenues', 'revenues_returns', 'cfo',
        'cfo_cov', 'capex', 'capex_cov', 'tax', 'intexp', 'intexp_cov'
    ]
    _MIN_DEPTH_DATA = 3

    def __init__(self, uid: str, past_horizon: int = 5, future_proj: int = 3,
                 perpetual_rate: float = 0., **kwargs):
        super().__init__(uid)

        self._idx = self._af.get(self._eq.index)
        self._ph = int(past_horizon)
        self._fp = int(future_proj)
        self._p_rate = perpetual_rate
        self._ff = Fin.FundamentalsFactory(self._comp)

        self._check_applicability()

        self._res_update(
            {
                'ccy': self._comp.currency,
                'perpetual_growth': self._p_rate,
                'uid': self._uid,
                'equity': self._eq.uid,
                'past_horizon': self._ph,
                'future_proj': self._fp
            }
        )

    def _check_applicability(self) -> None:
        y = min(
            len(self._ff.get_index(self.frequency)),
            self._ph
        )
        if y < self._MIN_DEPTH_DATA:
            raise ValueError(f'Not enough data found for {self._uid}')

        self._ph = y

    def _calc_freq(self) -> None:
        """ Calculate the frequency. """
        self._freq = 'A'

    def _otf_calculate(self, **kwargs) -> dict[str, Any]:
        """ Perform on-the-fly calculations. """
        return {}

    def _get_index(self) -> np.ndarray:
        f = self.frequency

        index = np.empty(self._ph + self._fp, dtype='datetime64[ns]')
        index[:self._ph] = self._ff.get_index(f)[-self._ph:]

        year = index[self._ph - 1].astype('datetime64[Y]') \
                   .astype(int) + 1970
        month = index[self._ph - 1].astype('datetime64[M]') \
                    .astype(int) % 12 + 1

        for i in range(self._ph, self._ph + self._fp):
            year += 1
            ts = pd.Timestamp(year, month, 15)
            dt = off.BMonthEnd().rollforward(ts)
            index[i] = dt.asm8

        return index

    def _calc_fcff(self) -> np.ndarray:
        f, ph = self.frequency, self._ph
        array = np.empty((len(self._COLS_FCF), ph + self._fp))
        array.fill(np.nan)

        # FCFF
        array[0, :ph] = self._ff.fcff(f)[1][-ph:]

        # REVENUES
        array[2, :ph] = self._ff.total_revenues(f)[1][-ph:]
        array[3, 1:ph] = array[2, 1:ph] / array[2, :ph - 1]
        mean_growth = np.nanmean(array[3, :ph])
        array[3, ph:] = mean_growth
        array[2, ph:] = mean_growth
        array[2, ph - 1:] = np.cumprod(array[2, ph - 1:])

        # CFO
        array[4, :ph] = self._ff._financial('OTLO', f)[1][-ph:]
        array[5, :ph] = array[4, :ph] / array[2, :ph]
        array[5, ph:] = np.nanmean(array[5, :ph])

        # CAPEX
        array[6, :ph] = self._ff._financial('SCEX', f)[1][-ph:]
        array[7, :ph] = array[6, :ph] / array[2, :ph]
        array[7, ph:] = np.nanmean(array[7, :ph])

        # TAX
        array[8, :ph] = self._ff.tax_rate(f)[1][-ph:]

        # INTEREST EXPENSE
        array[9, :ph] = self._ff.interest_expenses(f)[1][-ph:] \
                        * (1 - array[8, :ph])
        array[10, :ph] = array[9, :ph] / array[2, :ph]
        array[10, ph:] = np.nanmean(array[10, :ph])

        # FORECAST OF FCFF
        array[1, :] = (array[5, :] + array[10, :] - array[7, :]) \
                      * array[2, :]
        return array

    def _calc_wacc(self) -> tuple:
        f, ph = self.frequency, self._ph

        dt, equity = self._ff.total_equity(f)
        equity = equity[-1]
        debt = self._ff.total_debt(f)[1][-1]

        equity_share = equity / (equity + debt)
        debt_share = debt / (equity + debt)

        index = self._ff.get_index(f)[-self._ph:]
        capm = CAPM(self._eq).calculate(
            np.datetime64(str(index[0].astype('datetime64[Y]')) + '-01-01'),
            np.datetime64(str(index[-1].astype('datetime64[Y]')) + '-12-31')
        )
        coe = capm.capm_return

        rf = Fin.get_rf_glob() \
            .get_rf(self._eq.country) \
            .last_price()[0]

        rating = self._comp.rating.replace('+', '').replace('-', '') \
            if self._comp.rating else 'BB'
        uid = f'US_EY_{rating}_Corp'
        spread = self._af.get(uid).last_price()[0]

        taxes = self._ff.tax_rate(f)[1][-1]
        cod = (rf + spread) * (1 - taxes)
        wacc = coe * equity_share + cod * debt_share
        return wacc, coe, cod

    def _calculate(self) -> None:
        f, ph, fp = self.frequency, self._ph, self._fp
        fcff = self._calc_fcff()
        wacc, coe, cod = self._calc_wacc()

        # Get Cash Flows to discount
        cf = np.zeros((2, fp + 1))
        cf[0, :] = np.arange(1, fp + 2, 1)
        cf[1, :fp] = fcff[1, -fp:]
        cf[1, -1] = float(fcff[1, -1]) * (1. + self._p_rate) / \
                    (wacc - self._p_rate)

        # Calculate Fair Value
        shares = float(self._ff.common_shares(f)[1][-1])
        fair_value = float(np.sum(Math.dcf(cf, wacc))) / shares

        # Check whether the fair value is negative
        if fair_value < 0.:
            raise ValueError(f'Negative average fair value found {self._uid}')

        # Accumulate
        self._res_update(
            {
                'fcff_calc': pd.DataFrame(
                    fcff.T,
                    columns=self._COLS_FCF,
                    index=self._get_index()
                ),
                'last_price': self._last_price,
                'fair_value': fair_value,
                'ret': fair_value/self._last_price - 1.,
                'wacc': wacc,
                'cost_of_equity': coe,
                'cost_of_debt': cod,
                'history': ph,
                'projection': fp,
            }
        )


def DCFModel(uid: str, past_horizon: int = 5, future_proj: int = 3,
             perpetual_rate: float = 0.) -> DCFResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return DCF(
        uid,
        past_horizon,
        future_proj,
        perpetual_rate
    ).result()
