#
# Discounted Cash Flow Model
# Class to calculate a stock fair value using the DCF model
#

import cutils
import dataclasses
import numpy as np
import pandas as pd
import pandas.tseries.offsets as off
from scipy import stats
from typing import Optional

from nfpy.Calendar import (Frequency, Horizon)
import nfpy.Financial as Fin
from nfpy.Financial.SeriesStats import CAPM
import nfpy.IO.Utilities as Ut
import nfpy.Math as Math
from nfpy.Tools import Exceptions as Ex

from .BaseFundamentalModel import (BaseFundamentalModel, FundamentalModelResult)


@dataclasses.dataclass
class DCFResult(FundamentalModelResult):
    """ Object containing the results of the Discounted Cash Flow Model. """


class DCF(BaseFundamentalModel):
    """ Discounted Cash Flow Model class. """

    _RES_OBJ = DCFResult
    _COLS_FCF = [
        'fcf', 'calc_fcf', 'revenues', '\u0394% revenues', 'cfo',
        'cfo cov.', 'capex', 'capex cov.'
    ]
    _MIN_DEPTH_DATA = 3

    def __init__(
            self,
            uid: str,
            history: Horizon | str,
            future_horizon: Horizon | str,
            growth: Optional[float] = None,
            premium: Optional[float] = None,
            **kwargs
    ):
        super().__init__(uid)

        self._ff = Fin.FundamentalsFactory(self._comp)
        self._idx = self._af.get(self._eq.index)

        self._history = history \
            if isinstance(history, Horizon) else Horizon(history)
        self._projection = future_horizon \
            if isinstance(future_horizon, Horizon) else Horizon(future_horizon)

        self._growth = growth
        self._premium = premium
        gdp_w = kwargs.get('gdp_w', '20Y')
        self._gdp_w = gdp_w if isinstance(gdp_w, Horizon) else Horizon(gdp_w)

        if ((self._history.frequency != Frequency.Y)
                or (self._projection.frequency != Frequency.Y)
                or (self._gdp_w.frequency != Frequency.Y)):
            raise ValueError('DCF(): horizons must be in years')

    def _check_applicability(self) -> bool:
        """ Check applicability of the DDM model to the equity. The calendar
            length is compared to the history requirements.
        """
        # Check if yearly history is sufficient
        required_year = self._cal.t0y.year - self._gdp_w.years + 1
        if required_year < self._cal.yearly_calendar[0].year:
            raise Ex.CalendarError(f'DCF(): the yearly calendar is too short to have {self._gdp_w} of data')

        y = min(
            len(self._ff.get_index(self.frequency)),
            self._history.years
        )
        if y < self._history.years:
            if y < self._MIN_DEPTH_DATA:
                raise Ex.CalendarError(f'DCF(): Not enough historical data found for {self._uid}')
            else:
                msg = f'DCF(): Available data is only {y} years. Adjusted <history>.'
                Ut.print_wrn(Warning(msg))
                self._history = Horizon(f'{str(y)}Y')

        return True

    def _calc_freq(self) -> None:
        """ Calculate the frequency. """
        self._freq = 'A'

    def _otf_calculate(self, **kwargs) -> dict:
        """ Perform on-the-fly calculations. """
        return {}

    def _get_index(self) -> np.ndarray:
        f, ph, fp = self.frequency, self._history.years, self._projection.years

        index = np.empty(ph + fp, dtype='datetime64[ns]')
        index[:ph] = self._ff.get_index(f)[-ph:]

        year = int(index[ph - 1].astype('datetime64[Y]').astype(int) + 1970)
        month = int(index[ph - 1].astype('datetime64[M]').astype(int) % 12 + 1)

        for i in range(ph, ph + fp):
            year += 1
            ts = pd.Timestamp(year=year, month=month, day=15)
            dt = off.BMonthEnd().rollforward(ts)
            index[i] = dt.asm8

        return index

    def _calc_fcff_old(self) -> np.ndarray:
        f, ph = self.frequency, self._history.years
        array = np.empty((len(self._COLS_FCF), ph + self._projection.years))
        array.fill(np.nan)

        # FCFF
        array[0, :ph] = self._ff.fcff(f)[1][-ph:]

        # REVENUES
        array[2, :ph] = self._ff.total_revenues(f)[1][-ph:]
        array[3, 1:ph] = array[2, 1:ph] / array[2, :ph - 1] - 1.
        mean_growth = np.power(
            array[2, ph - 1] / array[2, 0],
            1. / (ph - 1)
        ) - 1.
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

    def _calc_fcff(self) -> np.ndarray:
        f, ph, fp = self.frequency, self._history.years, self._projection.years
        array = np.empty((len(self._COLS_FCF), ph + fp))
        array.fill(np.nan)

        # FCFF
        array[0, :ph] = self._ff.fcff(f)[1][-ph:]

        # REVENUES
        array[2, :ph] = self._ff.total_revenues(f)[1][-ph:]
        array[3, 1:ph] = array[2, 1:ph] / array[2, :ph - 1] - 1.
        # slope, itcp = stats.linregress(np.arange(1, ph), array[3, 1:ph])[:2]
        # array[3, ph:] = slope * np.arange(ph, ph + self._projection) + itcp
        # array[2, ph:] = array[3, ph:] + 1.
        mean_growth = np.power(
            array[2, ph - 1] / array[2, 0],
            1. / (ph - 1)
        ) - 1.
        array[3, ph:] = mean_growth
        slope, itcp = stats.linregress(np.arange(1, ph + 1), array[2, :ph])[:2]
        array[2, ph:] = slope * np.arange(ph, ph + fp) + itcp
        # array[2, ph - 1:] = np.cumprod(array[2, ph - 1:])

        # CFO
        array[4, :ph] = self._ff.cfo(f)[1][-ph:]
        array[5, :ph] = array[4, :ph] / array[2, :ph]
        slope, itcp = stats.linregress(np.arange(1, ph + 1), array[5, :ph])[:2]
        array[5, ph:] = slope * np.arange(ph, ph + fp) + itcp

        # CAPEX
        array[6, :ph] = self._ff.capex(f)[1][-ph:]
        array[7, :ph] = array[6, :ph] / array[2, :ph]
        slope, itcp = stats.linregress(np.arange(1, ph + 1), array[7, :ph])[:2]
        array[7, ph:] = slope * np.arange(ph, ph + fp) + itcp

        # FORECAST OF FCFF
        # The calculation assumes a negative CAPEX and that interest expenses
        # are still included in the CFO, so that do not need to be added back.
        array[1, :] = (array[5, :] + array[7, :]) * array[2, :]
        return array

    def _calc_growth(self) -> float:
        # Calculate the perpetual/long-term growth
        country = self._eq.country

        # Get GDP rate
        gdp = self._af \
                  .get_gdp(country, 'N') \
                  .prices \
                  .to_numpy()[:self._cal.xt0y + 1]
        n = gdp.shape[0]
        search_start = max(0, n - self._gdp_w.years)
        idx_gdp_start = cutils.next_valid_index(gdp, 0, search_start, n - 1)
        idx_gdp_end = cutils.last_valid_index(gdp, 0, search_start, n - 1)

        lt_gdp = np.power(
            gdp[idx_gdp_end] / gdp[idx_gdp_start],
            1. / (idx_gdp_end - idx_gdp_start)
        ) - 1.

        # Long-term drift
        return lt_gdp

    def _calc_wacc(self) -> tuple:
        f, ph = self.frequency, self._history

        dt, equity = self._ff.total_equity(f)
        equity = equity[-1]
        debt = self._ff.total_debt(f)[1][-1]

        equity_share = equity / (equity + debt)
        debt_share = debt / (equity + debt)

        capm = CAPM(
            self._eq,
            Frequency.M,
            horizon=self._history
        ).results(unlever=True)

        rf = self._af \
            .get_rf(self._eq.country) \
            .last_price()[0]

        rating = self._comp.rating.replace('+', '').replace('-', '') \
            if self._comp.rating else 'BB'
        uid = f'US_EY_{rating}_Corp'
        spread = self._af.get(uid).last_price()[0]

        taxes = self._ff.tax_rate(f)[1][-1]
        cod = (rf + spread) * (1 - taxes)
        wacc = capm.cost_of_equity * equity_share + cod * debt_share
        return wacc, capm, cod

    def _calculate(self) -> None:
        f, ph, fp = self.frequency, self._history.years, self._projection.years
        fcff = self._calc_fcff()
        wacc, capm, cod = self._calc_wacc()

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
        shares = self._ff.common_shares(f)[1][-1]
        fair_value = float(np.sum(Math.dcf(cf, wacc) / shares))

        # Check whether the fair value is negative
        if fair_value < 0.:
            success = False
            msg = 'Negative average fair value found'
        else:
            success = True
            msg = 'Evaluation successful'

        # Accumulate
        outputs = {
            'ccy': self._comp.currency,
            'equity': self._eq.uid,
            'fcff_calc': pd.DataFrame(
                fcff.T,
                columns=self._COLS_FCF,
                index=self._get_index(),
            ),
            'perpetual_growth': self._growth,
            'fair_value': fair_value,
            'ret': fair_value / self._last_price - 1.,
            'wacc': wacc,
            'cost_of_equity': capm.cost_of_equity,
            'cost_of_debt': cod,
            'lt_growth': lt_gwt,
            'tot_growth': tot_gwt,
            'risk_premium': capm.risk_premium,
            'beta': capm.beta,
            'risk_free': capm.rf
        }
        self._res = self._res_update(
            outputs=outputs,
            success=success,
            msg=msg
        )


def DCFModel(
        uid: str,
        past_horizon: Horizon,
        future_proj: Horizon,
        perpetual_rate: float = 0.
) -> DCFResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return DCF(
        uid,
        past_horizon,
        future_proj,
        perpetual_rate
    ).result()
