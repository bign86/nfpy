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

    def __init__(self, eq: TyAsset, suspension: float = .5,
                 start_date: Optional[np.datetime64] = None,
                 years: Optional[int] = None):
        """ Create an instance of the Dividend Factory.

            Input:
                eq [TyAsset]: dividend paying equity object (not UID)
                suspension [float]: factor used to determine whether dividends
                    have been suspended. It represents the percentage of the
                    confidence interval around the time distance between two
                    successive dividends (default 0.5)
                start_year [Optional[np.datetime64]: start from this here
                    instead of using all the available data. If defined has
                    priority over <years> (default None)
                years [Optional[int]]: use this number of years from the current
                    instead of using all the available data. Is overridden by
                    <start_date> if defined (default None)
        """

        # INPUTS
        self._eq = eq

        # WORKING VARIABLES
        # Flags + date
        self._t0 = None
        self._is_div_payer = False
        self._is_div_suspended = False

        # Dividends
        self._div = np.array([])
        self._div_dt = np.array([])
        self._num = 0

        # RESULTS
        # Derived quantities on regular dividends
        self._freq = 0
        self._slc = None
        self._yearly_slc = None

        # Annualized dividend quantities
        self._yearly_div = np.array([])
        self._yearly_dt = np.array([])
        self._yearly_count = np.array([])

        self._initialize(suspension, start_date, years)

    def _initialize(self, suspension: float = .5,
                    start_date: Optional[np.datetime64] = None,
                    years: Optional[int] = None) -> None:
        """ Initialize the factory. """
        if self._eq.type != 'Equity':
            msg = f'DividendFactory(): supports only equities not {self._eq.type}'
            raise ValueError(msg)

        # Initialize dividends stopping at t0
        div = self._eq.series('Dividend.SplitAdj.Regular').dropna()
        if div.empty:
            self._num = 0
            self._is_div_payer = False
            return

        # Select the data up to t0
        calendar = Cal.get_calendar_glob()
        t0 = calendar.t0.asm8.astype('datetime64[D]')
        self._t0 = t0

        slc = search_trim_pos(div.index.values, end=t0)
        self._div = div.values[slc]
        self._div_dt = div.index \
            .values[slc] \
            .astype('datetime64[D]')

        # Calculate the start date and get the number of usable dividends
        if start_date is None:
            if years is not None:
                start_date = t0 - np.timedelta64(years * Cn.DAYS_IN_1Y, 'D')
            else:
                start_date = self._div_dt[0]

        self._start_date = start_date \
            if start_date < calendar.start.asm8 \
            else calendar.start.asm8

        self._slc = search_trim_pos(div.index.values, start=self._start_date)
        self._num = len(self._div[self._slc])

        # Check if dividend payer, else quick exit
        self._is_div_payer = True if self._num > 0 else False
        if not self._is_div_payer:
            return

        # We transform the daily calendar as the yearly one may have a different
        # length.
        self._yearly_dt = np.unique(
            calendar.calendar
            .to_numpy()
            .astype('datetime64[Y]')
        )

        # If we have a single year it means there is no history enough to have
        # a yearly series. In this case we pass.
        size = self._yearly_dt.shape[0]
        if size > 1:
            self._yearly_slc = search_trim_pos(
                self._yearly_dt,
                start=self._start_date.astype('datetime64[Y]'),
                end=self._yearly_dt[-2]
            )

            self._yearly_div = np.zeros(size, dtype=float)
            self._yearly_count = np.zeros(size, dtype=int)

            start_year = self._yearly_dt[0].astype(int)
            for i in range(self._div.shape[0]):
                dt = self._div_dt[i].astype('datetime64[Y]').astype(int)
                pos = dt - start_year

                self._yearly_div[pos] += self._div[i]
                self._yearly_count[pos] += 1

            # Count the dividends paid per year and the frequency of payments
            for c in self._yearly_count[size - 2::-1]:
                if c in [1, 2, 4, 12]:
                    self._freq = c
                    break

            if self._freq == 0:
                self._freq = min(
                    [1, 2, 4, 12],
                    key=lambda v: abs(v - np.nanmean(self._yearly_div[:-1]))
                )

        # Check whether dividend is likely to have been suspended
        div_gap = (t0 - self._div_dt[-1]).astype(int)
        suspension_limit = max(suspension, .0) + 1.
        limit = Cn.DAYS_IN_1Y * suspension_limit / self.frequency
        if div_gap > limit:
            self._is_div_suspended = True

    def __len__(self) -> int:
        return self._num

    @property
    def all_annual_dividends(self) -> tuple[np.ndarray, np.ndarray]:
        return self._yearly_dt, self._yearly_div

    @property
    def all_dividends(self) -> tuple[np.ndarray, np.ndarray]:
        return self._div_dt, self._div

    @property
    def annual_dividends(self) -> tuple[np.ndarray, np.ndarray]:
        """ Returns the yearly dividend series beginning the starting date
            provided in input (if given) and ending last year. Current year is
            not considered as it is not possible to be sure that all dividends
            have been paid (some companies pay on an irregular schedule).
        """
        return self._yearly_dt[self._yearly_slc], self._yearly_div[self._yearly_slc]

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
        price_arr = prices.to_numpy()

        dt = self._yearly_dt[self._yearly_slc]
        idx = np.r_[
            np.searchsorted(prices.index.values, dt),
            price_arr.shape[0]
        ]

        # There is a corner case the 1st of january where the last two indexes
        # are the same giving rise to an extra spurious array element
        if idx[-1] == idx[-2]:
            idx = idx[:-1]

        idx_size = idx.shape[0]
        dy = np.empty(idx_size - 1)

        for i in range(0, idx_size - 1):
            dy[i] = self._yearly_div[i] / \
                    np.nanmean(price_arr[idx[i]:idx[i + 1]])
        dy[np.isnan(dy)] = .0

        return dt, dy

    def _calc_growth(self, horizon: int = 1) -> np.ndarray:
        """ Returns the dividend growth calculated over the selected period from
            the dividend series and projected over the horizon in input. The
            calculation is performed over annual dividends. The current year
            dividends are excluded from the calculation if not all paid to avoid
            an additional forecasting error in estimating the remaining dividends.

            If the issuer is not a dividend payer or the dividend is
            suspended, NaN is returned.

            Input:
                horizon [int]: future horizon on which to apply the
                    calculated growth. If 0 return current mean, if > 0 apply
                    the calculated trend and take the average (default 1)

            Output:
                growth [np.ndarray]: dividend growth over the horizon
        """
        # Quick exit if not a dividends payer
        if (not self._is_div_payer) | self._is_div_suspended:
            return np.nan

        # We check how many dividends have been paid in the current year vs the
        # frequency. If some are missing, we exclude the current year from the
        # calculation. It is possible that this creates an error when a company
        # pais dividends on a very uneven schedule (or no schedule at all).
        divs = self._yearly_div[self._yearly_slc]
        dt = self._yearly_dt[self._yearly_slc]
        if self._yearly_count[-1] < self._freq:
            divs = divs[:-1]
            dt = dt[:-1]

        # Check the resulting length
        if divs.shape[0] < 3:
            raise ValueError(
                f'DividendFactory(): at least 3 dividend payments required '
                f'({divs.shape[0]} provided) to calculate the dividend '
                f'growth of {self._eq.uid}'
            )

        # Calculate the returns
        ret = divs[1:] / divs[:-1] - 1.
        np.nan_to_num(ret, copy=False, posinf=np.nan)
        dt = dt[1:].astype(int)

        # Remove the outliers from the calculation, the tolerance band is set
        # to 2 sigmas. Repeat until ok.
        mask = [True]
        while np.any(mask):
            ret_mean = np.nanmean(ret)
            ret_std = 2. * np.nanstd(ret)
            up, low = ret_mean + ret_std, ret_mean - ret_std
            mask = (ret < low) | (ret > up)

            ret = ret[~mask]
            dt = dt[~mask]

        ret, mask = dropna(ret)
        dt = dt[mask]

        # Check if we still have enough data
        if ret.shape[0] < 2:
            raise ValueError(
                f'DividendFactory(): at least 3 dividend returns required after '
                f'after outliers cleaning ({ret.shape[0]} provided) to '
                f'calculate the dividend growth of {self._eq.uid}'
            )

        # Perform regression
        growth_mean = np.mean(ret)

        if horizon == 0:
            return growth_mean
        else:
            beta = stats.linregress(dt, ret)[0]

            return float(growth_mean) + beta * (1 + np.arange(abs(horizon)))

    @property
    def dividends(self) -> tuple[np.ndarray, np.ndarray]:
        """ Returns the dividend series beginning the starting date provided in
            input (if given) and ending at the last available dividend.
        """
        return self._div_dt[self._slc], self._div[self._slc]

    @property
    def dividends_special(self) -> tuple[np.ndarray, np.ndarray]:
        divs = self._eq.dividends_special.dropna()
        return (
            divs.values,
            divs.index.values.astype('datetime64[D]')
        )

    def div_yield(self, w: int) -> float:
        """ Returns the current dividend yield calculated as the TTM dividend
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

    def forecast(self, horizon: int = 1) -> tuple[np.ndarray, np.ndarray]:
        """ Performs a forecast of the future <num> dividends using a linear
            regression of the past history.

            Input:
                horizon [int]: future horizon on which to apply the
                    calculated growth. If 0 return current mean, if > 0 apply
                    the calculated trend and take the average (default 1)

            Output:
                dates [np.ndarray]: dates of the forecasted series
                divs [np.ndarray]: forecasted dividends

            Exception:
                ValueError: if neither <years> nor <start_year> are provided
                ValueError: if there is a single dividend in the series
        """
        growth = self._calc_growth(horizon)
        return self._yearly_div[-1] * np.cumprod(growth)

    @property
    def frequency(self) -> int:
        return self._freq

    def growth(self, horizon: int = 1) -> float:
        """ Returns the average dividend growth calculated over the selected
            period calculate from the dividend series and projected over the
            horizon in input. The calculation is performed over annual
            dividends. The current year dividends are excluded from the
            calculation if not all paid to avoid an additional error in
            forecasting the remaining dividends in the year.

            If the issuer is not a dividend payer or the dividend is
            suspended, NaN is returned.

            Input:
                horizon [int]: future horizon on which to apply the
                    calculated growth. If 0 return current mean, if > 0 apply
                    the calculated trend and take the average (default 1)

            Output:
                growth [float]: dividend growth
        """
        growth = self._calc_growth(horizon)

        if growth.shape[0] == 1:
            return growth[0]
        else:
            return .5 * (growth[0] + growth[-1])

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

        dt = (self._div_dt - self._div_dt[0]).astype(int)
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

    def ytd_div(self) -> float:
        """ Computes the YTD dividend. If the issuer is not a dividend payer, or
            the dividend is suspended zero is returned.

            Output:
                div [float]: dividend YTD
        """
        if (not self._is_div_payer) | self._is_div_suspended:
            return .0

        start = np.datetime64(str(self._t0.astype('datetime64[Y]')) + '-01-01')
        idx = np.searchsorted(self._div_dt, start)
        return float(np.sum(self._div[idx:]))

    def ytd_yield(self) -> float:
        """ Computes the YTD dividend yield. If the issuer is not a dividend
            payer, or the dividend is suspended zero is returned.

            Output:
                yield [float]: dividend yield YTD
        """
        if (not self._is_div_payer) | self._is_div_suspended:
            return .0

        start = np.datetime64(str(self._t0.astype('datetime64[Y]')) + '-01-01')

        prices = self._eq.series('Price.SplitAdj.Close')
        p = prices.values
        p_dt = prices.index.values

        idx_d = np.searchsorted(self._div_dt, start)
        idx_p = np.searchsorted(p_dt, start)

        return np.sum(self._div[idx_d:]) / np.nanmean(p[idx_p:])

