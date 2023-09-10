#
# Discounted Cash Flow Model
# Class to calculate a stock fair value using the DCF model
#

import numpy as np
import pandas as pd
import pandas.tseries.offsets as off
from scipy import stats
from typing import (Any, Optional)

import nfpy.Financial as Fin
import nfpy.Math as Math
from nfpy.Tools import Utilities as Ut

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
        'cfo_cov', 'capex', 'capex_cov'  # , 'tax', 'intexp', 'intexp_cov'
    ]
    _MIN_DEPTH_DATA = 3

    def __init__(self, uid: str, history: int = 10, future_proj: int = 5,
                 growth: Optional[float] = None, premium: Optional[float] = None,
                 **kwargs):
        super().__init__(uid)

        self._ff = Fin.FundamentalsFactory(self._comp)
        self._idx = self._af.get(self._eq.index)

        self._history = int(history)
        self._projection = int(future_proj)
        self._growth = growth
        self._premium = premium
        self._gdp_w = kwargs.get('gdp_w', 20)
        self._infl_w = kwargs.get('infl_w', 20)

        self._check_applicability()

    def _check_applicability(self) -> None:
        y = min(
            len(self._ff.get_index(self.frequency)),
            self._history
        )
        if y < self._history:
            if y < self._MIN_DEPTH_DATA:
                raise ValueError(f'Not enough historical data found for {self._uid}')
            else:
                msg = f'Available data is only {y} years. Adjusted <history>.'
                Ut.print_wrn(Warning(msg))
                self._history = y

    def _calc_freq(self) -> None:
        """ Calculate the frequency. """
        self._freq = 'A'

    def _otf_calculate(self, **kwargs) -> dict[str, Any]:
        """ Perform on-the-fly calculations. """
        return {}

    def _get_index(self) -> np.ndarray:
        f, ph, fp = self.frequency, self._history, self._projection

        index = np.empty(ph + fp, dtype='datetime64[ns]')
        index[:ph] = self._ff.get_index(f)[-ph:]

        year = index[ph - 1].astype('datetime64[Y]').astype(int) + 1970
        month = index[ph - 1].astype('datetime64[M]').astype(int) % 12 + 1

        for i in range(ph, ph + fp):
            year += 1
            ts = pd.Timestamp(year, month, 15)
            dt = off.BMonthEnd().rollforward(ts)
            index[i] = dt.asm8

        return index

    def _calc_fcff(self) -> np.ndarray:
        f, ph = self.frequency, self._history
        array = np.empty((len(self._COLS_FCF), ph + self._projection))
        array.fill(np.nan)

        # FCFF
        array[0, :ph] = self._ff.fcff(f)[1][-ph:]

        # REVENUES
        array[2, :ph] = self._ff.total_revenues(f)[1][-ph:]
        array[3, 1:ph] = array[2, 1:ph] / array[2, :ph - 1] - 1.
        mean_growth = np.nanmean(array[3, 1:ph])
        array[3, ph:] = mean_growth
        array[2, ph:] = mean_growth + 1.
        array[2, ph - 1:] = np.cumprod(array[2, ph - 1:])

        # CFO
        array[4, :ph] = self._ff.cfo(f)[1][-ph:]
        array[5, :ph] = array[4, :ph] / array[2, :ph]
        array[5, ph:] = np.nanmean(array[5, :ph])

        # CAPEX
        array[6, :ph] = self._ff.capex(f)[1][-ph:]
        array[7, :ph] = array[6, :ph] / array[2, :ph]
        array[7, ph:] = np.nanmean(array[7, :ph])

        # FORECAST OF FCFF
        # The calculation assumes a negative CAPEX and that interest expenses
        # are still included in the CFO, so that do not need to be added back.
        array[1, :] = (array[5, :] + array[7, :]) * array[2, :]
        return array

    def _calc_fcff_2(self) -> np.ndarray:
        f, ph = self.frequency, self._history
        array = np.empty((len(self._COLS_FCF), ph + self._projection))
        array.fill(np.nan)

        # FCFF
        array[0, :ph] = self._ff.fcff(f)[1][-ph:]

        # REVENUES
        array[2, :ph] = self._ff.total_revenues(f)[1][-ph:]
        array[3, 1:ph] = array[2, 1:ph] / array[2, :ph - 1] - 1.
        mean_growth = np.nanmean(array[3, 1:ph])
        array[3, ph:] = mean_growth
        array[2, ph:] = mean_growth + 1.
        array[2, ph - 1:] = np.cumprod(array[2, ph - 1:])

        # CFO
        array[4, :ph] = self._ff.cfo(f)[1][-ph:]
        array[5, :ph] = array[4, :ph] / array[2, :ph]
        slope = stats.linregress(np.arange(1, ph+1), array[5, :ph])[0]
        array[5, ph:] = slope * np.arange(1, self._projection+1) + array[5, ph - 1]

        # CAPEX
        array[6, :ph] = self._ff.capex(f)[1][-ph:]
        array[7, :ph] = array[6, :ph] / array[2, :ph]
        slope = stats.linregress(np.arange(1, ph+1), array[7, :ph])[0]
        array[7, ph:] = slope * np.arange(1, self._projection+1) + array[7, ph - 1]

        # FORECAST OF FCFF
        # The calculation assumes a negative CAPEX and that interest expenses
        # are still included in the CFO, so that do not need to be added back.
        array[1, :] = (array[5, :] + array[7, :]) * array[2, :]
        return array

    def _calc_growth(self) -> float:
        # Calculate the perpetual/long-term growth
        # Get GDP rate
        country = self._eq.country
        gdp_rate = self._rf \
            .get_gdp(country) \
            .prices.to_numpy()
        idx_gdp = self._gdp_w - 1
        lt_gdp = np.nanmean(gdp_rate[-idx_gdp:])

        # Get Inflation rate
        self._inflation = self._rf \
            .get_inflation(country) \
            .prices.to_numpy()
        idx_infl = (self._infl_w - 1) * 12
        lt_infl = np.nanmean(self._inflation[-idx_infl:])

        # Long-term drift
        return lt_gdp + lt_infl

    def _calc_wacc(self) -> tuple:
        f, ph = self.frequency, self._history

        dt, equity = self._ff.total_equity(f)
        equity = equity[-1]
        debt = self._ff.total_debt(f)[1][-1]

        equity_share = equity / (equity + debt)
        debt_share = debt / (equity + debt)

        index = self._ff.get_index(f)[-ph:]
        capm = CAPM(self._eq).calculate(
            np.datetime64(str(index[0].astype('datetime64[Y]')) + '-01-01'),
            np.datetime64(str(index[-1].astype('datetime64[Y]')) + '-12-31')
        )
        coe = capm.capm_return

        rf = self._rf \
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
        f, ph, fp = self.frequency, self._history, self._projection
        fcff = self._calc_fcff()
        wacc, coe, cod = self._calc_wacc()

        # Calculate growth
        lt_gwt = self._calc_growth() if self._growth is None else self._growth
        premium = .0 if self._premium is None else self._premium
        tot_gwt = lt_gwt + premium

        # Get Cash Flows to discount
        cf = np.zeros((2, fp + 1))
        cf[0, :] = np.arange(1, fp + 2, 1)
        cf[1, :fp] = fcff[1, -fp:]
        cf[1, -1] = float(fcff[1, -1]) * (1. + tot_gwt) / (wacc - tot_gwt)

        # Calculate Fair Value
        shares = float(self._ff.common_shares(f)[1][-1])
        fair_value = float(np.sum(Math.dcf(cf, wacc))) / shares

        # Check whether the fair value is negative
        if fair_value < 0.:
            raise ValueError(f'Negative average fair value found {self._uid}')

        # Accumulate
        self._res_update(
            {
                'ccy': self._comp.currency,
                'perpetual_growth': self._growth,
                'premium': self._premium,
                'uid': self._uid,
                'equity': self._eq.uid,
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
                'lt_growth': lt_gwt,
                'tot_growth': tot_gwt,
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
