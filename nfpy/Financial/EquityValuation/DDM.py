#
# Generic Dividend Discount Model
# Class to calculate a stock fair value using a multi-stage DDM
#

import numpy as np
import pandas as pd
from typing import Optional

import nfpy.Financial as Fin
import nfpy.Math as Math
from nfpy.Tools import (Exceptions as Ex, Utilities as Ut)

from .BaseFundamentalModel import (BaseFundamentalModel, FundamentalModelResult)


class DDMResult(FundamentalModelResult):
    """ Object containing the results of the Discounted Dividend Model family. """


class DDM(BaseFundamentalModel):
    """ Dividend Discount Model

        Up to three stages can be separately defined. The perpetual stage does
        not need to be defined. The syntax to specify one of the other two
        optional stages is described below. Stage2 can only be defined if stage1
        is defined as well.

        The short-term growth rate can be supplied in stage1. If not given, is
        calculated with one of the available methods using ROE as default.
        This is true regardless of the stage2 rate being supplied.

        Input:
            uid [str]: company or equity UID
            stage1 [Optional[tuple]]: first stage past GGM, defined as below (default: None)
            stage2 [Optional[tuple]]: second stage past GGM, defined as below (default: None)
                Stages are a tuple defined as (<t>, <g>, <H>) where:
                    - <t>: duration of the stage in years [mandatory]
                    - <g>: dividend growth [optional]
                    - <H>: is H-model stage [optional, default False]
            gwt_mode [Union[str, Sequence[str]]: one or a list as below (default: ROE):
                - historical: growth based on historical growth
                - ROE: growth based on financial statements
                - booth: growth based on macroeconomic factors
            gdp_w [int]: years of past gdp growth to estimate future gdp (default: 20)
            infl_w [int]: years of past inflation growth to estimate future
                inflation (default: 20)

            cost_equity [float]: discount factor, if None is calculated as the
                short-term inflation (default: None)
            premium [float]: premium applied on the cost of equity (default: 0)

        TODO:
            1. shares outstanding should be split adjusted
            2. check best approach for long-term growth
            3. recheck whether the max/min approach for LT/ST growth is appropriate
    """
    _RES_OBJ = DDMResult

    def __init__(self, uid: str, stage1: Optional[tuple] = None,
                 stage2: Optional[tuple] = None, **kwargs):
        super().__init__(uid)

        # Factories
        self._df = Fin.DividendFactory(self._eq)

        # Inputs
        if (stage1 is None) & (stage2 is not None):
            raise ValueError(f'DDM(): stage2 defined without a stage1 for {self._uid}')

        self._fp = sum(
            int(v[0])
            for v in (stage1, stage2)
            if v is not None
        )
        self._num_stages = sum(
            1 for v in (stage1, stage2)
            if v is not None
        )
        self._gdp_w = kwargs.get('gdp_w', 20)
        self._infl_w = kwargs.get('infl_w', 20)
        self._stage1 = stage1
        self._stage2 = stage2

        # We make a copy of the parameters as they may be modified and the
        # change would propagate outside the DDM model.
        self._growth_mode = kwargs.get('gwt_mode', []).copy()
        if isinstance(self._growth_mode, str):
            self._growth_mode = [self._growth_mode]
        elif isinstance(self._growth_mode, tuple):
            self._growth_mode = list(self._growth_mode)

        # Add the manual mode if a manual value was given in stage1
        if stage1 is not None:
            if stage1[1] is not None:
                self._growth_mode.append('manual')

        # If there is no mode activated use default ROE
        if len(self._growth_mode) == 0:
            self._growth_mode.append('ROE')

        # Outputs - methods specific
        self._no_growth = {}
        self._manual_growth = {}
        self._historical_growth = {}
        self._ROE_growth = {}

        # Outputs - general
        self._div_ts = None
        self._dt = None
        self._im_ke = None
        self._im_lt_premium = None
        self._im_st_premium = None
        self._inflation = None
        self._lt_growth = None

        self._check_applicability()

    def _calculate(self) -> None:
        """ Calculate the short-term and long-term dividend growth using one of
            the supported methodologies:
                1. Average dividend growth adjusted for short-term tendency
                2. Average retention rate times ROE
                3. Booth model (1998)
                4. Linear regression of dividends paid (NOT IMPLEMENTED)
        """
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
        self._lt_growth = lt_gdp + lt_infl

        # Calculate:
        # - the implied cost of equity (from GGM)
        # - premium over long-term inflation
        # - premium over short-term inflation
        _, yd = self._df.annual_dividends
        self._im_ke = yd[-1] * (1. + self._lt_growth) / self._last_price \
                      + self._lt_growth
        self._im_lt_premium = self._im_ke - lt_infl
        self._im_st_premium = self._im_ke - \
                              Math.last_valid_value(self._inflation)[0]

        # Calculate the dates of the future dividends
        dt0, d0 = self._df.last
        t = np.arange(1., round(self._fp * self.frequency) + .001)
        self._dt = [
            dt0 + np.timedelta64(round(12 * v / self._freq), 'M').astype('timedelta64[D]')
            for v in t
        ]

        # Calculate the no-growth part of the model, independent of the growth
        # calculation methodology.
        if self._num_stages == 0:
            self._no_growth['cf'] = d0 * self._freq

        else:
            # Create the no-growth arrays
            cf = d0 + np.zeros(t.shape[0])
            self._no_growth['pn'] = d0 * self._freq
            self._no_growth['cf'] = np.array([t, cf])

        # Calculate the short-term dividend growth and the model results given
        # the methodology.
        if 'manual' in self._growth_mode:
            self._manual_growth['st_gwt'] = self._stage1[1]
            self._calc_future_divs_growth(self._manual_growth, t, d0)
        if 'historical' in self._growth_mode:
            try:
                self._calc_historical_g(self._stage1[0])
                self._calc_future_divs_growth(self._historical_growth, t, d0)
            except ValueError as ex:
                Ut.print_exc(ex)
        if 'ROE' in self._growth_mode:
            self._calc_roe_g(yd)
            self._calc_future_divs_growth(self._ROE_growth, t, d0)

        # Calculate the series for plotting
        divs = self._df.dividends
        self._div_ts = pd.Series(divs[1], index=divs[0])

    def _calc_freq(self) -> None:
        """ Calculates model frequency. """
        self._freq = self._df.frequency

    def _calc_future_divs_growth(self, data: dict, t: np.ndarray, d0: float) -> None:

        # If there are suitable stages, go through them
        if self._num_stages == 0:
            data['cf'] = self._no_growth['cf'] * (1. + self._lt_growth)

        else:
            fut_rate = np.ones(t.shape[0])
            inv_freq = 1. / self._freq
            rate_lt_pp = Math.compound(self._lt_growth, inv_freq)
            rate_1 = data['st_gwt']

            if self._num_stages == 1:
                rate_1_pp = Math.compound(rate_1, inv_freq)
                fut_rate += rate_1_pp

                if self._stage1[2]:
                    fut_rate -= (rate_1_pp - rate_lt_pp) * (t - 1) / t[-1]

            else:
                rate_2 = self._stage2[1]
                if rate_2 is None:
                    rate_2 = (rate_1 + self._lt_growth) / 2.

                t_1 = self._stage1[0] * self._freq

                rate_1_pp = Math.compound(rate_1, inv_freq)
                rate_2_pp = Math.compound(rate_2, inv_freq)

                if self._stage1[2]:
                    fut_rate[:t_1] += (rate_2_pp - rate_1_pp) * \
                                      (t[:t_1] - 1) / t[t_1 - 1]

                if self._stage2[2]:
                    if not self._stage1[2]:
                        rate_2_pp = rate_1_pp

                    rate_v = (rate_lt_pp - rate_2_pp) * \
                             (t[t_1:] - t[t_1]) / (len(t) - t[t_1 - 1])
                    rate_v[np.isnan(rate_v)] = .0
                    fut_rate[t_1:] += rate_v

                fut_rate[:t_1] += rate_1_pp
                fut_rate[t_1:] += rate_2_pp

            data['rates'] = Math.compound((fut_rate - 1.), self._freq)

            # Calculate the compounded dividends
            fut_rate[0] *= d0
            cf_growth = np.cumprod(fut_rate)

            # Calculate the perpetual part
            data['pn'] = float(cf_growth[-1]) \
                             * (1. + self._lt_growth) \
                             * self._freq
            data['cf'] = np.array([t, cf_growth])

    def _calc_fv(self, data: dict, den: float, ke: float) -> dict:
        """ In input give the annual required rate of return. """

        if self._num_stages == 0:
            fv = float(data['cf'] / den)
        else:
            ke_per_period = Math.compound(ke, 1. / self._freq)

            cf = data['cf'].copy()
            cf[1, -1] += data['pn'] / den
            fv = float(np.sum(Math.dcf(cf, ke_per_period)))

        ret = fv / self._last_price - 1.

        res = data.copy()
        res['fv'] = fv
        res['ret'] = ret
        return res

    def _calc_historical_g(self, horizon: int) -> None:
        """ Calculates the growth as the average dividend growth YoY. """
        try:
            st_growth = self._df.growth(horizon=horizon)
        except ValueError as ex:
            self._growth_mode.remove('historical')
            raise ex

        self._historical_growth['st_gwt'] = st_growth

    def _calc_roe_g(self, yd: np.ndarray) -> None:
        """ Calculates the growth as: g = (1 - D/NI) * ROE """
        ff = Fin.FundamentalsFactory(self._comp)
        try:
            dt, eq = ff.total_equity('A')
            _, ni = ff.net_income('A')
            _, so = ff.common_shares('A')

            # FIXME: the values should be split-adjusted
            ni_ps = ni / so[-1]
            eq_ps = eq / so[-1]

            n = min(yd.shape[0], eq.shape[0])
            growth = (ni_ps[-n:] - yd[-n:]) / eq_ps[-n:]

            annual_drift = np.nanmean(growth)
            macro_growth = pd.Series(growth, index=dt[-n:])
        except ValueError:
            annual_drift = .0
            macro_growth = pd.Series([], dtype=float)

        self._ROE_growth['st_gwt'] = annual_drift
        self._ROE_growth['macro_growth'] = macro_growth

    def _check_applicability(self) -> None:
        """ Check applicability of the DDM model to the equity. The presence
            and frequency of dividends is checked.
        """
        # Validate the dividend growth calculation mode
        if len(set(self._growth_mode) - {'manual', 'historical', 'ROE', 'booth'}) > 0:
            raise ValueError(
                f'DDM(): dividend growth methodology not recognized for {self._eq.uid}'
            )

        # We assume DDM cannot be used if dividends are NOT paid
        if not self._df.is_dividend_payer:
            raise Ex.MissingData(f'DDM(): {self._eq.uid} is not a dividend payer')

        # If the last dividend was outside the tolerance for the inferred
        # frequency, assume the dividend has been suspended
        if self._df.is_dividend_suspended:
            msg = f'DDM(): Dividends for {self._uid} [{self._eq.uid}] appear to have been suspended'
            raise Ex.MissingData(msg)

    def _otf_calculate(self, ke: Optional[float] = None,
                       premium: Optional[float] = None, **kwargs) -> dict:
        """ Calculate equity cost and denominator for the perpetual dividend.
            In input give the annual required rate of return. If not supplied,
            the equity cost is calculated as:
                dr = inflation + premium
        """
        premium = .0 if premium is None else premium
        if ke is None:
            ke, _ = Math.last_valid_value(self._inflation)
        ke += premium

        # Calculate denominator and check model consistency
        den = ke - self._lt_growth
        if den <= 0.:
            msg = f'Ke={ke:.1%} < g={self._lt_growth:.1%} for {self._uid}'
            raise ValueError(msg)

        final_res = {
            # General
            'uid': self._uid,
            'ccy': self._eq.currency,
            'stages': self._num_stages,

            # Historical
            'last_price': self._last_price,
            'div_ts': self._div_ts,

            # Implied
            'implied_ke': self._im_ke,
            'implied_lt_premium': self._im_lt_premium,
            'implied_st_premium': self._im_st_premium,

            # Common future
            'ke': ke,
            'premium': premium,
            'dates': self._dt,
            'lt_growth': self._lt_growth,

            # No-growth results
            'no_growth': self._calc_fv(
                self._no_growth, den, ke
            ),
        }

        # Finalize calculations for each methodology.
        if 'manual' in self._growth_mode:
            final_res['manual_growth'] = self._calc_fv(
                self._manual_growth, den, ke
            )
        if 'historical' in self._growth_mode:
            final_res['historical_growth'] = self._calc_fv(
                self._historical_growth, den, ke
            )
        if 'ROE' in self._growth_mode:
            final_res['ROE_growth'] = self._calc_fv(
                self._ROE_growth, den, ke
            )

        return final_res


def DDMModel(company: str, stage1: Optional[tuple] = None,
             stage2: Optional[tuple] = None,
             ke: Optional[float] = None,
             premium: Optional[float] = None) -> DDMResult:
    """ Shortcut for the DDM calculation. Intermediate results are lost. """
    return DDM(company, stage1, stage2).result(cost_equity=ke, premium=premium)


def GGMModel(company: str, ke: Optional[float] = None,
             premium: Optional[float] = None) -> DDMResult:
    """ Shortcut for the GGM calculation. Intermediate results are lost. """
    return DDM(company, stage1=None, stage2=None) \
        .result(cost_equity=ke, premium=premium)
