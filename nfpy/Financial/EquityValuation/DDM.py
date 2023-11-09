#
# Generic Dividend Discount Model
# Class to calculate a stock fair value using a multi-stage DDM
#

import cutils
import dataclasses
import numpy as np
import pandas as pd
from typing import Optional

import nfpy.Financial as Fin
import nfpy.Math as Math
from nfpy.Tools import (Exceptions as Ex, Utilities as Ut)

from .BaseFundamentalModel import (BaseFundamentalModel, FundamentalModelResult)


@dataclasses.dataclass
class DDMResult(FundamentalModelResult):
    """ Object containing the results of the Discounted Dividend Model family. """


class DDM(BaseFundamentalModel):
    """ Dividend Discount Model

        Up to two stages can be separately defined. The perpetual stage does
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
            div_w [int]: year of past dividends to estimate future (default: 5)
            infl_w [int]: years of past inflation growth to estimate future
                inflation (default: 20)
            gdp_w [int]: years of past gdp growth to estimate future gdp (default: 20)

            cost_equity [float]: discount factor, if None is calculated as the
                short-term inflation (default: None)
            premium [float]: premium applied on the cost of equity (default: 0)

        TODO:
            1. shares outstanding should be split adjusted
            2. check best approach for long-term growth
            3. recheck whether the max/min approach for LT/ST growth is appropriate
    """
    _RES_OBJ = DDMResult
    _GROWTH_MODELS = {
        'manual': False,
        'historical': False,
        'ROE': False,
    }

    def __init__(self, uid: str, stage1: Optional[tuple] = None,
                 stage2: Optional[tuple] = None, **kwargs):
        super().__init__(uid)

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
        self._div_w = kwargs.get('div_w', 5)
        self._gdp_w = kwargs.get('gdp_w', 20)
        self._infl_w = kwargs.get('infl_w', 20)
        self._stage1 = stage1
        self._stage2 = stage2

        # We make a copy of the parameters as they may be modified and the
        # change would propagate outside the DDM model.
        self._growth_models = self._GROWTH_MODELS.copy()
        input_growth_models = kwargs.get('gwt_mode', []).copy()

        # Validate the dividend growth calculation mode
        if len(set(input_growth_models) - {'manual', 'historical', 'ROE'}) > 0:
            raise ValueError(
                f'DDM(): dividend growth methodology not recognized for {self._eq.uid}'
            )

        if isinstance(input_growth_models, str):
            self._growth_models[input_growth_models] = True
        elif isinstance(input_growth_models, (tuple, list)):
            for model in input_growth_models:
                self._growth_models[model] = True

        # Add the manual mode if a manual value was given in stage1
        if stage1 is not None:
            if stage1[1] is not None:
                self._growth_models['manual'] = True

        # If there is no mode activated use default ROE
        if not any(self._growth_models.values()):
            self._growth_models['ROE'] = True

        # Factories
        self._df = Fin.DividendFactory(self._eq, years=self._div_w)

        # Outputs - methods specific
        self._no_growth = {}
        self._manual_growth = {}
        self._historical_growth = {}
        self._ROE_growth = {}

        # Outputs - general
        self._st_inflation = None
        self._lt_growth = None

    def _calculate(self) -> None:
        """ Calculate the short-term and long-term dividend growth using one of
            the supported methodologies:
                1. Average dividend growth adjusted for short-term tendency
                2. Average retention rate times ROE
                3. Booth model (1998)
        """
        country = self._eq.country

        # Long-term drift is the nominal GDP
        gdp = self._fnf \
                  .get_gdp(country, 'N') \
                  .prices \
                  .to_numpy()[:self._cal.xt0y + 1]
        n = gdp.shape[0]
        search_start = max(0, n - self._gdp_w)
        idx_gdp_start = cutils.next_valid_index(gdp, 0, search_start, n - 1)
        idx_gdp_end = cutils.last_valid_index(gdp, 0, search_start, n - 1)

        self._lt_growth = np.power(
            gdp[idx_gdp_end] / gdp[idx_gdp_start],
            1. / (idx_gdp_end - idx_gdp_start)
        ) - 1.

        # Get Inflation rate
        inflation = self._fnf \
                        .get_inflation(country) \
                        .prices \
                        .to_numpy()[:self._cal.xt0m + 1]
        n = inflation.shape[0]
        search_start = max(0, n - self._infl_w * 12)
        idx_infl_start = cutils.next_valid_index(inflation, 0, search_start, n - 1)
        idx_infl_end = cutils.last_valid_index(inflation, 0, search_start, n - 1)
        lt_infl = np.nanmean(inflation[idx_infl_start:idx_infl_end + 1])
        self._st_inflation = inflation[idx_infl_end]

        # Calculate the dates of the future dividends
        yearly_dt, yearly_d = self._df.annual_dividends
        dtY0 = yearly_dt[-1]
        dY0 = yearly_d[-1]
        t = np.arange(1., self._fp + .001, dtype=int)

        # Calculate the no-growth part of the model, independent of the growth
        # calculation methodology.
        if self._num_stages == 0:
            self._no_growth['cf'] = dY0

        else:
            # Create the no-growth arrays
            cf = dY0 + np.zeros(t.shape[0])
            self._no_growth['pn'] = dY0
            self._no_growth['cf'] = np.array([t, cf])

        # Calculate the short-term dividend growth and the model results given
        # the methodology.
        if self._growth_models['manual']:
            self._manual_growth['st_gwt'] = self._stage1[1]
            self._calc_future_divs_growth(self._manual_growth, t, dY0)
        if self._growth_models['historical']:
            try:
                self._calc_historical_g()
                self._calc_future_divs_growth(self._historical_growth, t, dY0)
            except ValueError as ex:
                Ut.print_exc(ex)
        if self._growth_models['ROE']:
            self._calc_roe_g()
            self._calc_future_divs_growth(self._ROE_growth, t, dY0)

        #
        # Record the outputs
        #

        # Calculate:
        # - the implied cost of equity (from GGM)
        # - premium over long-term inflation
        # - premium over short-term inflation
        _, yd = self._df.annual_dividends
        im_ke = yd[-1] * (1. + self._lt_growth) / self._last_price \
                + self._lt_growth
        divs = self._df.dividends

        outputs = {
            'ccy': self._eq.currency,
            'div_ts': pd.Series(divs[1], index=divs[0]),
            'dates': [
                dtY0 + np.timedelta64(v, 'Y').astype('timedelta64[D]')
                for v in t
            ],
            'lt_growth': self._lt_growth,
            'lt_inflation': lt_infl,
            'st_inflation': self._st_inflation,
            'implied_ke': im_ke,
            'implied_lt_premium': im_ke - lt_infl,
            'implied_st_premium': im_ke - self._st_inflation
        }
        self._res = self._res_update(outputs=outputs)

    def _calc_freq(self) -> None:
        """ Calculates model frequency. """
        self._freq = self._df.frequency

    def _calc_future_divs_growth(self, data: dict, t: np.ndarray, dY0: float) -> None:

        # If there are suitable stages, go through them
        if self._num_stages == 0:
            data['cf'] = self._no_growth['cf'] * (1. + self._lt_growth)

        else:
            fut_rate = np.ones(t.shape[0])
            rate_1 = data['st_gwt']

            if self._num_stages == 1:
                fut_rate += rate_1

                if self._stage1[2]:
                    fut_rate -= (rate_1 - self._lt_growth) * (t - 1) / t[-1]

            else:
                rate_2 = self._stage2[1]
                if rate_2 is None:
                    rate_2 = (rate_1 + self._lt_growth) / 2.

                t_1 = self._stage1[0]

                if self._stage1[2]:
                    fut_rate[:t_1] += (rate_2 - rate_1) * \
                                      (t[:t_1] - 1) / t[t_1 - 1]

                if self._stage2[2]:
                    if not self._stage1[2]:
                        rate_2 = rate_1

                    rate_v = (self._lt_growth - rate_2) * \
                             (t[t_1:] - t[t_1]) / (len(t) - t[t_1 - 1])
                    rate_v[np.isnan(rate_v)] = .0
                    fut_rate[t_1:] += rate_v

                fut_rate[:t_1] += rate_1
                fut_rate[t_1:] += rate_2

            data['rates'] = fut_rate - 1.

            # Calculate the compounded dividends
            fut_rate[0] *= dY0
            cf_growth = np.cumprod(fut_rate)

            # Calculate the perpetual part
            data['pn'] = float(cf_growth[-1]) \
                         * (1. + self._lt_growth)
            data['cf'] = np.array([t, cf_growth])

    def _calc_fv(self, data: dict, den: float, ke: float) -> dict:
        """ In input give the annual required rate of return. """

        if self._num_stages == 0:
            fv = float(data['cf'] / den)
        else:
            cf = data['cf'].copy()
            cf[1, -1] += data['pn'] / den
            fv = float(np.sum(Math.dcf(cf, ke)))

        ret = fv / self._last_price - 1.

        res = data.copy()
        res['fv'] = fv
        res['ret'] = ret
        return res

    def _calc_historical_g(self) -> None:
        """ Calculates the growth as the average dividend growth YoY. """
        try:
            st_growth = self._df.growth()
        except ValueError as ex:
            self._growth_models['historical'] = False
            raise ex

        self._historical_growth['st_gwt'] = st_growth

    def _calc_roe_g(self) -> None:
        """ Calculates the growth as: g = (1 - D/NI) * ROE """
        ff = Fin.FundamentalsFactory(self._comp)
        try:
            _, ni = ff.net_income('A')
            _, td = ff.cash_dividends_paid('A')
            _, roe = ff.roe('A')

            n = min(td.shape[0], ni.shape[0])
            _roe = np.nanmean(roe[-n:])
            _td = np.nanmean(td[-n:])
            _ni = np.nanmean(ni[-n:])
            annual_drift = _roe * (1 + _td / _ni)

        except ValueError:
            annual_drift = .0

        self._ROE_growth['st_gwt'] = annual_drift

    def _check_applicability(self) -> bool:
        """ Check applicability of the DDM model to the equity. The presence
            and frequency of dividends is checked. The calendar length is
            compared to the history requirements.
        """

        # We assume DDM cannot be used if dividends are NOT paid
        if not self._df.is_dividend_payer:
            self._res.msg = f'Not a dividend payer'
            return False

        # If the last dividend was outside the tolerance for the inferred
        # frequency, assume the dividend has been suspended
        if self._df.is_dividend_suspended:
            msg = f'Dividends appear to have been suspended'
            self._res.msg = msg
            return False

        # Check if monthly history is sufficient
        required_month = self._cal.t0m.asm8.astype('datetime64[M]') \
                         - np.timedelta64(self._infl_w * 12 - 1, 'M')
        if required_month < self._cal.monthly_calendar[0].asm8.astype('datetime64[M]'):
            raise Ex.CalendarError(f'DDM(): the yearly calendar is too short to have {self._infl_w} years of data')

        # Check if yearly history is sufficient
        required_year = self._cal.t0y.year - self._gdp_w + 1
        if required_year < self._cal.yearly_calendar[0].year:
            raise Ex.CalendarError(f'DDM(): the yearly calendar is too short to have {self._gdp_w} years of data')

        return True

    def _otf_calculate(self, ke: Optional[float] = None,
                       premium: Optional[float] = None, **kwargs) -> dict:
        """ Calculate equity cost and denominator for the perpetual dividend.
            In input give the annual required rate of return. If not supplied,
            the equity cost is calculated as:
                dr = inflation + premium
        """
        premium = .0 if premium is None else premium
        if ke is None:
            ke = self._st_inflation
        ke += premium

        # Calculate denominator and check model consistency
        den = ke - self._lt_growth
        if den <= 0.:
            msg = f'Ke={ke:.1%} < g={self._lt_growth:.1%} for {self._uid}'
            raise ValueError(msg)

        final_res = {
            'ke': ke,
            'no_growth': self._calc_fv(
                self._no_growth, den, ke
            )
        }

        if self._growth_models['manual']:
            final_res['manual_growth'] = self._calc_fv(
                self._manual_growth, den, ke
            )
        if self._growth_models['historical']:
            final_res['historical_growth'] = self._calc_fv(
                self._historical_growth, den, ke
            )
        if self._growth_models['ROE']:
            final_res['ROE_growth'] = self._calc_fv(
                self._ROE_growth, den, ke
            )

        return {
            'outputs': final_res,
            'success': True,
            'msg': 'Evaluation successful'
        }


def DDMModel(company: str, stage1: Optional[tuple] = None,
             stage2: Optional[tuple] = None, ke: Optional[float] = None,
             premium: Optional[float] = None) -> DDMResult:
    """ Shortcut for the DDM calculation. Intermediate results are lost. """
    return DDM(company, stage1, stage2).result(cost_equity=ke, premium=premium)


def GGMModel(company: str, ke: Optional[float] = None,
             premium: Optional[float] = None) -> DDMResult:
    """ Shortcut for the GGM calculation. Intermediate results are lost. """
    return DDM(company, stage1=None, stage2=None) \
        .result(cost_equity=ke, premium=premium)
