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
from nfpy.Tools import Constants as Cn

from .BaseFundamentalModel import (BaseFundamentalModel, FundamentalModelResult)


class DCFResult(FundamentalModelResult):
    """ Object containing the results of the Discounted Cash Flow Model. """

    @property
    def fcf(self) -> pd.Series:
        return self.df['fcf']

    @property
    def net_income(self) -> pd.Series:
        return self.df['net_income']

    @property
    def fcf_coverage(self) -> pd.Series:
        return self.df['fcf_coverage']

    @property
    def revenues(self) -> pd.Series:
        return self.df['revenues']

    @property
    def revenues_returns(self) -> pd.Series:
        return self.df['revenues_returns']

    @property
    def net_income_margin(self) -> pd.Series:
        return self.df['net_income_margin']

    @property
    def total_debt(self) -> pd.Series:
        return self.df['total_debt']

    @property
    def tax_rate(self) -> pd.Series:
        return self.df['tax_rate']

    @property
    def cost_of_debt(self) -> pd.Series:
        return self.df['cost_of_debt']

    @property
    def beta(self) -> pd.Series:
        return self.df['beta']

    @property
    def market_return(self) -> pd.Series:
        return self.df['market_return']

    @property
    def cost_of_equity(self) -> pd.Series:
        return self.df['cost_of_equity']

    @property
    def wacc(self) -> pd.Series:
        return self.df['wacc']


class DiscountedCashFlowModel(BaseFundamentalModel):
    """ Discounted Cash Flow Model class. """

    _RES_OBJ = DCFResult
    _COLS = ['fcf', 'net_income', 'fcf_coverage', 'revenues', 'revenues_returns',
             'net_income_margin', 'total_debt', 'tax_rate', 'cost_of_debt',
             'beta', 'market_return', 'cost_of_equity', 'wacc']
    _MAX_TAX_R = .25
    _MIN_TAX_R = .0
    _MIN_DEPTH_DATA = 3
    _MIN_DEBT_COST = .05

    def __init__(self, uid: str, past_horizon: int = 5, future_proj: int = 3,
                 perpetual_rate: float = 0., **kwargs):
        super().__init__(uid)

        self._idx = self._af.get(self._eq.index)
        self._ph = int(past_horizon)
        self._fp = int(future_proj)
        self._p_rate = max(perpetual_rate, .0)
        self._ff = Fin.FundamentalsFactory(self._comp)

        self._fcf = None

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
        f = self.frequency
        y = min(
            len(self._ff.get_index(f)),
            self._ph
        )
        if y < self._MIN_DEPTH_DATA:
            raise ValueError(f'Not enough data found for {self._uid}')

        # If negative average FCFE exit
        fcf = self._ff.fcfe(f)[1][-y:]
        if (fcf < 0.).any():
            raise ValueError(f'Negative average Free Cash Flow found for {self._uid}')

        self._ph = y
        self._fcf = fcf

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

    def _calc_fcf_coverage(self, array: np.array) -> None:
        f, y = self.frequency, self._ph

        # Get Free Cash Flow and Net Income
        net_inc = self._ff.net_income(f)[1][-y:]

        # Get FCF coverage and its average
        cov = self._fcf / net_inc
        if y > 3:
            cov_min = np.nanargmin(cov)
            cov_max = np.nanargmax(cov)
            idx = [
                i for i in range(0, y)
                if (i != cov_max) and (i != cov_min)
            ]
            # FIXME: we should check that after accounting for nans, there are
            #        at least 2 data points left
            mean_fcfcov_margin = np.nanmean(cov[idx])
        else:
            mean_fcfcov_margin = np.nanmean(cov)

        array[0, :y] = self._fcf
        array[1, :y] = net_inc
        array[2, :y] = cov
        array[2, y:] = mean_fcfcov_margin

    def _calc_revenues(self, array: np.array) -> None:
        f, y, p = self.frequency, self._ph, self._fp

        rev = np.empty(y + p)
        rev[:y] = self._ff.total_revenues(f)[1][-y:]
        ret = rev[1:y] / rev[:y - 1]
        mean_ret = np.nanmean(ret)
        rev[y:] = mean_ret
        rev[y - 1:] = np.cumprod(rev[y - 1:])

        array[3, :] = rev
        array[4, 1:y] = ret
        array[4, y:] = mean_ret

    def _calculate(self) -> None:
        """ Perform main calculations. """
        f, y, yj = self.frequency, self._ph, self._fp
        array = np.empty((len(self._COLS), y + yj))
        array.fill(np.nan)
        index = self._get_index()

        # Get Free Cash Flow and Revenues
        self._calc_fcf_coverage(array)
        self._calc_revenues(array)

        # Get Net Income margin and their projection
        array[5, :y] = array[1, :y] / array[3, :y]
        mean_ni_margin = np.mean(np.maximum(array[5, :y], .0))
        array[5, y:] = mean_ni_margin

        # Get Net Income and Free Cash Flow projection
        array[1, y:] = array[3, y:] * mean_ni_margin
        array[0, y:] = array[1, y:] * array[2, y:]

        # Get Total Debt
        array[6, :y] = self._ff.total_liabilities(f)[1][-y:]

        # Get Tax Rate
        # self._calc_tax_rate(array)
        array[7, :y] = self._ff.tax_rate(f)[1][-y:]

        # Get Cost of Debt (floored)
        array[8, :y] = np.maximum(
            (self._ff.interest_expenses(f)[1][-y:] / array[6, :y])
            * (1. - array[7, :y]),
            self._MIN_DEBT_COST
        )

        # Get Beta for Cost of Equity
        beta = np.empty(y)
        returns = self._eq.returns
        b_returns = self._idx.returns
        for i, dt in enumerate(index[:y]):
            year = dt.astype('datetime64[Y]').astype(int) + 1970
            try:
                beta[i] = Math.beta(
                    returns.index.values,
                    returns.values,
                    b_returns.values,
                    start=np.datetime64(f'{str(year)}-01-01'),
                    end=dt
                )[1]
            except ValueError:
                beta[i] = .0
        mean_beta = np.mean(beta[np.where(beta != 0)])
        beta[beta == 0] = np.mean(beta[np.where(beta != 0)])
        array[9, :y] = beta

        # Get Market and RF returns for Cost of Equity
        for n, dt in enumerate(index[:y]):
            year = dt.astype('datetime64[Y]').astype(int) + 1970
            start = np.datetime64(f'{str(year)}-01-01')
            array[10, n] = Math.compound(
                self._idx.expct_return(
                    start=start,
                    end=dt
                ),
                Cn.BDAYS_IN_1Y
            )

        # Get Cost of Equity
        array[11, :y] = np.maximum(
            array[9, :y] * array[10, :y],
            .0
        )

        # Get WACC
        total_asset = self._ff.total_asset(f)[1][-y:]

        total_value = total_asset + array[6, :y]
        array[12, :y] = array[8, :y] * (array[6, :y] / total_value) + \
                        array[11, :y] * (total_asset / total_value)
        mean_wacc = np.maximum(np.mean(array[12, :y]), .05)
        # Put a floor = .05 to the WACC
        array[12, y:] = mean_wacc

        # Get Cash Flows to discount
        cf = np.zeros((2, yj + 1))
        cf[0, :] = np.arange(1, yj + 2, 1)
        cf[1, :yj] = array[0, -yj:]
        cf[1, -1] = float(array[0, -1:]) * (1. + self._p_rate) / \
                    max(mean_wacc - self._p_rate, .025)

        # Calculate Fair Value
        shares = float(self._ff.common_shares(f)[1][-1])
        fair_value = float(np.sum(Math.dcf(cf, mean_wacc))) / shares

        # Accumulate
        self._res_update(
            {
                'df': pd.DataFrame(
                    array.T,
                    columns=self._COLS,
                    index=index
                ),
                'fair_value': fair_value,
                'shares': shares,
                'mean_wacc': mean_wacc,
                'mean_beta': mean_beta,
            }
        )


def DCFModel(uid: str, past_horizon: int = 5, future_proj: int = 3,
             perpetual_rate: float = 0.) -> DCFResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return DiscountedCashFlowModel(
        uid,
        past_horizon,
        future_proj,
        perpetual_rate
    ).result()
