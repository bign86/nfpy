#
# Dividends factory class
# Methods to deal with dividends
#

import numpy as np
from scipy import stats
from typing import Optional

from nfpy.Assets import TyAsset
import nfpy.Calendar as Cal
from nfpy.Math import (dropna, search_trim_pos)
from nfpy.Tools import Constants as Cn

_DAYS_FREQ_T = (
    Cn.DAYS_IN_1Y,
    Cn.DAYS_IN_1Q * 2,
    Cn.DAYS_IN_1Q,
    Cn.DAYS_IN_1M
)
_DAYS_FREQ_D = {
    1: Cn.DAYS_IN_1Y,
    2: Cn.DAYS_IN_1Q * 2,
    4: Cn.DAYS_IN_1Q,
    12: Cn.DAYS_IN_1M
}


class DividendFactory(object):

    def __init__(self, eq: TyAsset, suspension: float = 1.):
        # INPUTS
        self._eq = eq
        self._suspension = max(suspension, .0) + 1.

        # WORKING VARIABLES
        # Flags + date
        self._t0 = Cal.get_calendar_glob().t0.asm8
        self._is_div_payer = False
        self._is_div_suspended = False

        # Dividends
        self._div = np.array([])
        self._div_dt = np.array([])
        self._num = 0

        # RESULTS
        # Derived quantities on regular dividends
        self._dist = np.array([])
        self._freq = 0

        # Annualized dividend quantities
        self._yearly_div = np.array([])
        self._yearly_dt = np.array([])

        self._initialize()

    def _initialize(self) -> None:
        """ Initialize the factory. """
        if self._eq.type != 'Equity':
            msg = f'DividendFactory() supports only equities not {self._eq.type}'
            raise ValueError(msg)

        # Initialize dividends stopping at t0
        div = self._eq.series('Dividend.SplitAdj.Regular').dropna()
        if div.empty:
            self._num = 0
            self._is_div_payer = False
            return

        slc = search_trim_pos(
            div.index.values,
            end=Cal.pd_2_np64(Cal.get_calendar_glob().t0)
        )
        self._div = div.values[slc]
        self._num = len(self._div)
        self._is_div_payer = True if self._num > 0 else False

        # If not dividend payer, quick exit
        if not self._is_div_payer:
            return

        self._div_dt = div.index \
            .values[slc] \
            .astype('datetime64[D]')

        if self._num > 1:
            self._dist = np.diff(self._div_dt)

        # Calculate frequency
        div_dt_y = self._div_dt.astype('datetime64[Y]')
        counts = np.unique(div_dt_y, return_counts=True)[1]
        self._freq = min(
            [1, 2, 4, 12],
            key=lambda v: abs(v - np.mean(counts))
        )

        # Get series of years
        self._yearly_dt = np.arange(
            str(div_dt_y[0].astype('int') + 1970),
            str(Cal.today().year + 1),
            dtype='datetime64[Y]'
        )
        years_idx = np.searchsorted(self._div_dt, self._yearly_dt)
        if years_idx[-1] != self._div_dt.shape[0]:
            years_idx = np.r_[years_idx, self._div_dt.shape[0]]

        # Calculate yearly dividend as a sum
        divs = np.zeros(self._yearly_dt.shape)
        for n in range(years_idx.shape[0] - 1):
            divs[n] += np.sum(self._div[years_idx[n]:years_idx[n + 1]])

        # Adjust the first year using the inferred frequency
        divs[-1] *= self._freq / counts[-1]
        self._yearly_div = divs

        # Check whether dividend is likely to have been suspended
        t0 = self._t0.astype('datetime64[D]')
        div_gap = (t0 - self._div_dt[-1]).astype(int)
        limit = Cn.DAYS_IN_1Y * self._suspension / self.frequency
        if div_gap > limit:
            self._is_div_suspended = True

    def __len__(self) -> int:
        return self._num

    @property
    def annual_dividends(self) -> tuple[np.ndarray, np.ndarray]:
        return self._yearly_dt, self._yearly_div

    def annual_yields(self) -> tuple[np.ndarray, np.ndarray]:
        """ Computes the series of annual dividend yields as annual dividend
            over the average equity price over the year (YTD for the current
            year). If the issuer is not a dividend payer, two empty arrays will
            be returned.

            Output:
                year [np.ndarray]: series of years
                yield [np.ndarray]: dividend yield for each year
        """
        if not self._is_div_payer:
            return np.array([]), np.array([])

        prices = self._eq.series('Price.SplitAdj.Close')

        dt = np.r_[
            self._yearly_dt,
            np.datetime64(str(self._yearly_dt[-1] + 1) + '-01-01')
        ]
        idx = np.searchsorted(prices.index.values, dt)
        dy = np.empty(len(idx) - 1)

        for i in range(1, idx.shape[0]):
            dy[i - 1] = self._yearly_div[i - 1] / \
                        np.nanmean(prices.values[idx[i - 1]:idx[i]])

        return self._yearly_dt, dy

    @property
    def distance(self) -> np.array:
        return self._dist

    @property
    def dividends(self) -> tuple[np.ndarray, np.ndarray]:
        return self._div_dt, self._div

    @property
    def dividends_special(self) -> tuple[np.ndarray, np.ndarray]:
        divs = self._eq.dividends_special.dropna()
        return (
            divs.values,
            divs.index.values.astype('datetime64[D]')
        )

    def div_yield(self, w: int) -> float:
        """ Returns the current dividend yield calculated as the TTMM dividend
            over the average price calculated on the given window. If not a
            dividend payer or if dividend has been suspended, it returns 0.

            Input:
                w [int]: window of daily prices to calculate the average price

            Output:
                dy [float]: dividend yield
        """
        # Quick exit if not a dividends payer
        if (not self._is_div_payer) | self._is_div_suspended:
            return .0

        price = np.nanmean(
            self._eq.series('Price.SplitAdj.Close')
            .values[-abs(w):]
        )
        return self.ttm_div() / price

    def forecast(self, num: int, years: Optional[int] = None,
                 start_year: Optional[int] = None) \
            -> tuple[np.ndarray, np.ndarray]:
        """ Performs a forecast of the future <num> dividends using a linear
            regression of the past history.

            Input:
                num [int]: number of dividends to forecast
                years [Optional[int]]: number of years to use
                start_year [Optional[int]]: start year of the series to use

            Output:
                dates [np.ndarray]: dates of the forecasted series
                divs [np.ndarray]: forecasted dividends

            Exception:
                ValueError: if neither <years> nor <start_year> are provided
                ValueError: if there is a single dividend in the series
        """
        slope, intercept = self.regression(years, start_year)
        if np.isnan(slope):
            return np.ndarray([]), np.ndarray([])

        # FIXME: for longer forecasts, the error due to 1Y == 360D accumulates
        dt = np.arange(1, num + 1) * _DAYS_FREQ_D[self._freq]

        divs = intercept + slope * dt
        dt = self._div_dt[-1] + dt.astype('timedelta64[D]')

        return dt, divs

    @property
    def frequency(self) -> int:
        return self._freq

    def growth(self, years: Optional[int] = None,
               start_year: Optional[int] = None) -> float:
        """ Returns the annual dividend growth calculated from the annual
            dividend series. If at least one dividend has been paid in the
            current year, the year is considered for the calculation using the
            inferred annual dividend.
            Example: if the first quarterly dividend of 3$ has been paid out,
            the annual dividend is assumed to be 12$.
            Priority in the inputs is given to <start_year>.

            If the issuer is not a dividend payer or the dividend is
            suspended, NaN is returned.

            Input:
                years [Optional[int]]: number of years to use
                start_year [Optional[int]]: start year of the series to use

            Output:
                dr [Optional[float]]: drift of the yields

            Exceptions:
                ValueError: if neither <years> nor <start_year> are provided
                ValueError: if there is a single dividend in the series
        """
        # Quick exit if not a dividends payer
        if (not self._is_div_payer) | self._is_div_suspended:
            return np.nan

        # Check inputs
        if (years is None) & (start_year is None):
            msg = f'DividendFactory(): either <years> or <start_year> must be provided.'
            raise ValueError(msg)

        if start_year is None:
            start_year = Cal.today().year - years
        start_dt = str(start_year) + '-01-01'

        # Search the start of the series and exclude nans
        start_dt = np.datetime64(start_dt) \
            .astype('datetime64[Y]')
        idx = np.searchsorted(self._yearly_dt, start_dt)

        # If this year dividend has not been paid yet, not consider it
        if self._yearly_div[-1] == .0:
            idx = max(idx-1, 0)
            end = -1
        else:
            end = None

        yd, mask = dropna(
            self._yearly_div[idx:end]
        )

        # Check the resulting length
        if yd.shape[0] < 2:
            msg = f'DividendFactory(): at least 2 years of dividends required ' \
                  f'({yd.shape[0]} provided) for the dividend drift of {self._eq.uid}'
            raise ValueError(msg)

        # The number of return periods is the number of yields - 1 plus any
        # missing yield but the very first if missing.
        length = yd.shape[0] + np.sum(~mask[1:]) - 1
        return (yd[-1] / yd[0]) ** (1. / length) - 1.

    @property
    def is_dividend_payer(self) -> bool:
        return self._is_div_payer

    @property
    def is_dividend_suspended(self) -> bool:
        return self._is_div_suspended

    @property
    def last(self) -> tuple[Optional[np.datetime64], float]:
        """ Returns the last *regular* dividend paid even if dividends appear
            suspended. If the issuer does not pay dividends a <None, .0> is
            returned.
        """
        if not self._is_div_payer:
            return None, .0
        return self._div_dt[-1], self._div[-1]

    @property
    def num(self) -> int:
        return self.__len__()

    def payout_ratio(self):
        pass

    def regression(self, years: Optional[int] = None,
                   start_year: Optional[int] = None) -> tuple[float, float]:
        """ Performs a regression on the series of dividends. The results may be
            used to forecast the future path of dividends.

            Input:
                years [Optional[int]]: number of years to use
                start_year [Optional[int]]: start year of the series to use

            Output:
                slope [float]: slope of the regression
                intercept [float]: intercept of the regression

            Exception:
                ValueError: if neither <years> nor <start_year> are provided
                ValueError: if there is a single dividend in the series
        """
        # Quick exit if not a dividends payer
        if (not self._is_div_payer) | self._is_div_suspended:
            return np.nan, np.nan

        # Check inputs
        if (years is None) & (start_year is None):
            msg = f'DividendFactory(): either <years> or <start_year> must be provided.'
            raise ValueError(msg)

        if start_year is None:
            start_year = Cal.today().year - years

        # Search the start of the series and exclude nans
        start_date = np.datetime64(
            str(start_year) + '-01-01'
        ).astype('datetime64[D]')
        idx = np.searchsorted(self._div_dt, start_date)
        divs, mask = dropna(self._div[idx:])
        dts = self._div_dt[idx:][mask]

        # Check the resulting length
        if divs.shape[0] < 2:
            msg = f'DividendFactory(): at least 2 dividends required ' \
                  f'for the regression of {self._eq.uid} dividends'
            raise ValueError(msg)

        days = (dts - dts[-1]).astype(int)
        return stats.linregress(days, divs)[:2]

    def search_sp_div(self, tolerance: float = .1) -> tuple:
        """ Function to search for special dividends. Creates a grid of
            plausible dates when to pay a dividend given the inferred frequency.
            The distance between the actual payment date and the theoretical one
            determines whether a dividend is classified as potentially special.
        """
        if not self._is_div_payer:
            return np.array([]), np.array([]), .0

        if tolerance > 1. or tolerance < 0.:
            msg = f'Tolerance for dividends should be in [0, 1], given {tolerance}'
            raise ValueError(msg)

        dt = (self._div_dt - self._div_dt[0]).astype('int')
        days = Cn.DAYS_IN_1Y / self.frequency
        grid = np.round(dt / days) * days
        anomaly = 2 * np.abs(dt - grid) / days

        exp = - 10. * (anomaly - .5)
        prob = 1. / (1. + np.exp(exp))

        return (
            self._div_dt[prob > tolerance],
            self._div[prob > tolerance],
            prob
        )

    def ttm_div(self) -> float:
        """ Computes the TTM dividend. If the issuer is not a dividend payer, or
            the dividend is suspended zero is returned.

            Output:
                div [float]: dividend TTM
        """
        if (not self._is_div_payer) | self._is_div_suspended:
            return .0

        start = self._t0 - np.timedelta64(Cn.DAYS_IN_1Y, 'D')
        idx = np.searchsorted(self._div_dt, start)
        return float(np.sum(self._div[idx:]))

    def ttm_payout_ratio(self):
        pass

    def ttm_yield(self) -> float:
        """ Computes the TTM dividend yield. If the issuer is not a dividend
            payer, or the dividend is suspended zero is returned.

            Output:
                yield [float]: dividend yield TTM
        """
        if (not self._is_div_payer) | self._is_div_suspended:
            return .0

        start = self._t0 - np.timedelta64(Cn.DAYS_IN_1Y, 'D')

        prices = self._eq.series('Price.SplitAdj.Close')
        p = prices.values
        p_dt = prices.index.values

        idx_d = np.searchsorted(self._div_dt, start)
        idx_p = np.searchsorted(p_dt, start)

        return np.sum(self._div[idx_d:]) / np.nanmean(p[idx_p:])
