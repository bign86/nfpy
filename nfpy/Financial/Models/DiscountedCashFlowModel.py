#
# Discounted Cash Flow Model
# Class to calculate a stock fair value using the DCF model
#

import numpy as np
import pandas as pd
from typing import Union

import nfpy.Math as Mat
from nfpy.Tools import (Constants as Cn, Utilities as Ut)

from .BaseFundamentalModel import BaseFundamentalModel
from ..FundamentalsFactory import FundamentalsFactory


class DCFResult(Ut.AttributizedDict):
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
    _MAX_TAX_R = .15
    _MIN_TAX_R = .10
    _MIN_DEPTH_DATA = 3

    def __init__(self, company: str, date: Union[str, pd.Timestamp] = None,
                 past_horizon: int = 5, future_proj: int = 3,
                 date_fmt: str = '%Y-%m-%d', perpetual_rate: float = 0.):
        super().__init__(company, date, past_horizon, future_proj, date_fmt)
        self._p_rate = max(perpetual_rate, .0)
        self._fcf = None

        self._ff = FundamentalsFactory(self._cmp)
        self._check_applicability()

        self._res_update(ccy=self._cmp.currency, perpetual_growth=self._p_rate,
                         uid=self._cmp.uid, equity=self._eq.uid, t0=self._t0,
                         start=self._start, past_horizon=self._ph,
                         future_proj=self._fp)

    def _check_applicability(self):
        f, y = self.frequency, self._ph

        actual_y = len(self._ff.get_index(f))
        y = min(actual_y, y)
        if y < self._MIN_DEPTH_DATA:
            raise ValueError('Not enough data found for {}'
                             .format(self._cmp.uid))

        # If negative average FCF exit
        fcf = self._ff.fcf(f).values[-y:]
        # if np.nanmean(fcf) < 0.:
        if (fcf < 0.).any():
            raise ValueError('Negative average Free Cash Flow found for {}'
                             .format(self._cmp.uid))

        self._ph = y
        self._fcf = fcf

    def _calc_freq(self):
        """ Calculate the frequency. """
        self._freq = 'A'

    def _otf_calculate(self, **kwargs) -> dict:
        """ Perform on-the-fly calculations. """
        return {}

    def _get_index(self):
        f, y, p = self.frequency, self._ph, self._fp

        past = self._ff.get_index(f)[-y:]
        curr = int(past[-1].year) + 1
        future = pd.DatetimeIndex([pd.Timestamp(y, 12, 31)
                                   for y in range(curr, curr + p)])
        return past.append(future)

    def _calc_fcf_coverage(self, array: np.array):
        f, y = self.frequency, self._ph

        # Get Free Cash Flow and Net Income
        net_inc = self._ff.net_income(f).values[-y:]

        # Get FCF coverage and its average
        cov = self._fcf / net_inc
        if y > 3:
            cov_min = np.nanargmin(cov)
            cov_max = np.nanargmax(cov)
            idx = [i for i in range(0, y)
                   if i != cov_max and i != cov_min]  # and ~np.isnan(i)]
            # FIXME: we should check that after accounting for nans, there are
            #        at least 2 data points left
            mean_fcfcov_margin = np.nanmean(cov[idx])
        else:
            mean_fcfcov_margin = np.nanmean(cov)

        array[0, :y] = self._fcf
        array[1, :y] = net_inc
        array[2, :y] = cov
        array[2, y:] = mean_fcfcov_margin

    def _calc_revenues(self, array: np.array):
        f, y, p = self.frequency, self._ph, self._fp

        rev = np.empty(y + p)
        rev[:y] = self._ff.tot_revenues(f).values[-y:]
        ret = rev[1:y] / rev[:y - 1]
        mean_ret = np.nanmean(ret)
        rev[y:] = mean_ret
        rev[y - 1:] = np.cumprod(rev[y - 1:])

        array[3, :] = rev
        array[4, 1:y] = ret
        array[4, y:] = mean_ret

    def _calc_tax_rate(self, array: np.array):
        f, y = self.frequency, self._ph

        tax_rate = self._ff.income_tax_paid(f).values[-y:] / \
                   self._ff.income_before_taxes(f).values[-y:]
        # Put a floor = .0 and a cap = .25 to the tax rate
        tax_rate = np.maximum(np.minimum(tax_rate, self._MAX_TAX_R),
                              self._MIN_TAX_R)
        array[7, :y] = tax_rate

    def _calculate(self):
        """ Perform main calculations. """
        f, y, yj = self.frequency, self._ph, self._fp
        array = np.zeros((len(self._COLS), y + yj))
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
        array[6, :y] = self._ff.tot_debt(f).values[-y:]

        # Get Tax Rate
        self._calc_tax_rate(array)

        # Get Cost of Debt
        cod = (self._ff.interest_expenses(f).values[-y:] /
               array[6, :y]) * (1. - array[7, :y])
        # Put a floor = .0 to the cost of debt
        array[8, :y] = np.maximum(cod, .05)

        # Get Beta for Cost of Equity
        # beta = []
        beta = np.empty(y)
        for i, dt in enumerate(index[:y]):
            try:
                beta[i] = self._eq.beta(start=pd.Timestamp(dt.year, 1, 1),
                                        end=dt)[1]
            except ValueError:
                beta[i] = .0
        # beta = np.array(beta)
        mean_beta = np.mean(beta[np.where(beta != 0)])
        beta[beta == 0] = mean_beta
        array[9, :y] = beta

        # Get Market and RF returns for Cost of Equity
        array[10, :y] = np.array([Mat.compound(self._idx.expct_return(
            start=pd.Timestamp(dt.year, 1, 1), end=dt),
            Cn.BDAYS_IN_1Y) for dt in index[:y]])

        # Get Cost of Equity
        coe = array[9, :y] * array[10, :y]
        array[11, :y] = np.maximum(coe, .0)

        # Get WACC
        total_asset = self._ff.tot_asset(f).values[-y:]
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
        den = max(mean_wacc - self._p_rate, .025)
        cf[1, -1] = float(array[0, -1:]) * (1. + self._p_rate) / den

        # Calculate Fair Value
        shares = float(self._ff.total_shares(f).values[-1])
        fair_value = float(np.sum(Mat.dcf(cf, mean_wacc))) / shares

        # Accumulate
        self._res_update(df=pd.DataFrame(array.T, columns=self._COLS,
                         index=index), fair_value=fair_value, shares=shares,
                         mean_wacc=mean_wacc, mean_beta=mean_beta,
                         last_price=self.get_last_price())
