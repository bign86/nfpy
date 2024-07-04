#
# Dividends factory class
# Methods to deal with dividends
#

import cutils
import numpy as np

from nfpy.Assets import TyAsset
import nfpy.Calendar as Cal
from nfpy.Math import search_trim_pos
from nfpy.Tools import (Constants as Cn, Exceptions as Ex)

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

    def __init__(
            self,
            eq: TyAsset,
            suspension: float = .5
    ):
        """ Create an instance of the Dividend Factory.

            Input:
                eq [TyAsset]: dividend paying equity object (not UID)
                suspension [float]: factor used to determine whether dividends
                    have been suspended. It represents the percentage of the
                    confidence interval around the time distance between two
                    successive dividends (default 0.5)
                start_date [Optional[np.datetime64]: start from this date
                    instead of using all the available data. If defined has
                    priority over <years> (default None)
                years [Optional[int]]: use this number of years before t0
                    instead of using all the available data. Is overridden by
                    <start_date> if defined (default None)
        """

        # INPUTS
        self._eq = eq

        # WORKING VARIABLES
        # Flags + date
        self._t0 = None
        self._is_div_payer = True
        self._is_div_suspended = False

        # Dividends
        self._div = np.array([])
        self._div_dt = np.array([])
        self._num = 0

        # RESULTS
        # Derived quantities on regular dividends
        self._freq = 0

        # Annualized dividend quantities
        self._yearly_div = np.array([])
        self._yearly_dt = np.array([])
        self._yearly_count = np.array([])
        self._yearly_num = 0

        self._initialize(suspension)

    def _initialize(self, suspension: float = .5) -> None:
        """ Initialize the factory. """
        if self._eq.type != 'Equity':
            msg = f'DividendFactory(): supports only equities not {self._eq.type}'
            raise ValueError(msg)

        # Initialize dividends stopping at t0
        div_series = self._eq.series('Dividend.SplitAdj.Regular').dropna()
        if div_series.empty:
            self._is_div_payer = False
            return

        self._num = len(div_series)
        div = div_series.to_numpy()
        div_dt = div_series.index.to_numpy().astype('datetime64[D]')

        calendar = Cal.get_calendar_glob()
        t0 = calendar.t0.asm8.astype('datetime64[D]')
        self._t0 = t0
        self._div = div
        self._div_dt = div_dt

        # Create the yearly series according to the existing dividend data.
        yearly_dt = np.unique(div_dt.astype('datetime64[Y]'))

        # Since we dropped NaNs from the dividend's series, any year of with no
        # payments has been removed. Therefore, we make sure to generate the
        # full series to cover any gaps.
        size = yearly_dt.shape[0]
        start_y = yearly_dt[0].astype(int)
        end_y = yearly_dt[-1].astype(int)
        if size < (end_y - start_y) + 1:
            yearly_dt = np.array(
                [
                    np.datetime64(str(v + 1970)).astype('datetime64[Y]')
                    for v in range(start_y, end_y + 1)
                ]
            )
            size = yearly_dt.shape[0]
        elif size > (end_y - start_y) + 1:
            raise ValueError(
                f'Dividends._initialize(): inconsistency in generating yearly dividends for {self._eq.uid}')

        yearly_div = np.zeros(size, dtype=float)
        yearly_count = np.zeros(size, dtype=int)

        # Fill-in the yearly series
        for i in range(div.shape[0]):
            dt = div_dt[i].astype('datetime64[Y]').astype(int)
            pos = dt - start_y
            yearly_div[pos] += div[i]
            yearly_count[pos] += 1

        # If the yearly series contains the current year, remove it
        if yearly_dt[-1] > calendar.t0y.asm8.astype('datetime64[Y]'):
            yearly_div = yearly_div[:-1]
            yearly_dt = yearly_dt[:-1]
            yearly_count = yearly_count[:-1]
            size = yearly_dt.shape[0]

            # If the only yearly dividend available is for the current year,
            # eliminating it will leave an empty series. Then exit.
            if size == 0:
                return

        # If the calendar is longer than the payment history of the company, the
        # 0s at the beginning of the series should not be treated as if the
        # company suspended the dividends, but should not count at all. Hence,
        # we substitute the (potential) initial zeros w/ NaNs.
        pay_start = 0
        while yearly_count[pay_start] == 0:
            pay_start += 1
        yearly_div[:pay_start] = np.nan

        # Count the dividends paid per year to infer the frequency of payments.
        # TODO: This frequency may change over the years in which case we will
        #       get the wrong frequency for a few years. Solutions:
        #         1. Give higher weight to recent observations
        #         2. Store in the database the frequency in an extra column
        freq = 0
        if size > 1:
            last_div = size - 2
            while last_div >= pay_start:
                if yearly_count[last_div] in [1, 2, 4, 12]:
                    freq = yearly_count[last_div]
                    break
                last_div = last_div - 1

            if freq not in [1, 2, 4, 12]:
                freq = min(
                    [1, 2, 4, 12],
                    key=lambda v: abs(v - np.nanmean(yearly_div[pay_start:-1]))
                )

            # Check whether dividend is likely to have been suspended
            div_gap = (t0 - div_dt[-1]).astype(int)
            suspension_limit = max(suspension, .0) + 1.
            limit = Cn.DAYS_IN_1Y * suspension_limit / freq
            if div_gap > limit:
                self._is_div_suspended = True

        self._freq = freq
        self._yearly_div = yearly_div
        self._yearly_dt = yearly_dt
        self._yearly_count = yearly_count
        self._yearly_num = size

    def __len__(self) -> int:
        return self._num

    def yearly_len(self) -> int:
        return self._yearly_num

    @property
    def annual_dividends(self) -> tuple[np.ndarray, np.ndarray]:
        """ Returns the yearly dividend series beginning the starting date
            provided in input (if given) and ending last year. Current year is
            not considered as it is not possible to be sure that all dividends
            have been paid (some companies pay on an irregular schedule).
        """
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
        price_arr = prices.to_numpy()

        idx = np.r_[
            np.searchsorted(prices.index.values, self._yearly_dt),
            price_arr.shape[0]
        ]

        # There is a corner case the 1st of january where the last two indexes
        # are the same giving rise to an extra spurious array element
        idx_size = idx.shape[0]
        if idx_size > 1:
            if idx[-1] == idx[-2]:
                idx = idx[:-1]
                idx_size = idx_size - 1

        dy = np.empty(idx_size - 1)

        for i in range(0, idx_size - 1):
            dy[i] = self._yearly_div[i] / \
                    np.nanmean(price_arr[idx[i]:idx[i + 1]])
        dy[np.isnan(dy)] = .0

        return self._yearly_dt, dy

    def _calc_mean_growth(self, years: int | None) -> float:
        """ Returns the average dividend growth calculated over the selected
            period calculated from the dividend series. The calculation is
            performed over annual dividends. The current year dividends are
            excluded from the calculation if not all paid to avoid an additional
            error in forecasting the remaining dividends in the year.

            Input:
                years [Optional[int]]: past history to use to calculate growth.

            Output:
                growth [float]: dividend growth
        """
        divs = self._yearly_div

        # We eliminate all dividends market as NaN
        first_valid_year = cutils.next_valid_index(divs, 0, 0, divs.shape[0])
        divs = divs[first_valid_year:]

        # Consider the right amount of history years
        if years is not None:
            if divs.shape[0] > years:
                divs = divs[-years:]

        # Check the resulting length
        if divs.shape[0] < 2:
            raise Ex.MissingData(
                f'DividendFactory(): at least 2 dividend payments required '
                f'({divs.shape[0]} provided) to calculate the dividend '
                f'growth of {self._eq.uid}'
            )

        # Calculate the returns
        ret = divs[1:] / divs[:-1] - 1.
        np.nan_to_num(ret, copy=False, posinf=np.nan)
        ret = cutils.dropna(ret, 1)

        # Remove the outliers from the calculation
        ret_mean = np.mean(ret)
        ret_std = 2. * np.std(ret)
        up, low = ret_mean + ret_std, ret_mean - ret_std
        if (ret[0] < low) or (ret[0] > up):
            ret = ret[1:]

        # Check if we still have enough data
        if ret.shape[0] < 1:
            raise ValueError(
                f'DividendFactory(): at least 1 dividend returns required after '
                f'after outliers cleaning ({ret.shape[0]} provided) to '
                f'calculate the dividend growth of {self._eq.uid}'
            )

        # Perform regression
        return float(np.mean(ret))

    @property
    def dividends(self) -> tuple[np.ndarray, np.ndarray]:
        """ Returns the dividend series. """
        return self._div_dt, self._div

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

    def forecast(
            self,
            horizon: int,
            years: int | None = None,
            mode: str = 'mean'
    ) -> np.ndarray:
        """ Performs a forecast of the future <num> dividends using a linear
            regression of the past history.

            Input:
                horizon [int]: future horizon on which to apply the
                    calculated growth. Must be > 0.
                years [Optional[int]]: past history length to use to forecast
                    (min 2). If None, all available data are used.
                mode [str]: mode of calculation. (Default "mean").

            Output:
                dates [np.ndarray]: dates of the forecasted series
                divs [np.ndarray]: forecasted dividends

            Exception:
                ValueError: if neither <years> nor <start_year> are provided
                ValueError: if there is a single dividend in the series
        """
        # Input checks
        if horizon < 1:
            raise ValueError(f'DividendFactory.forecast(): at least 1 years of horizon needed ({horizon} given)')

        growth = self.growth(years, mode)
        growth = np.ones(horizon, dtype=float) + growth

        return self._yearly_div[-2] * np.cumprod(growth)

    @property
    def frequency(self) -> int:
        return self._freq

    def growth(
            self,
            years: int | None = None,
            mode: str = 'mean'
    ) -> float:
        """ Returns the average dividend growth calculated over the selected
            period calculated from the dividend series. The calculation is
            performed over annual dividends. The current year dividends are
            excluded from the calculation if not all paid to avoid an additional
            error in forecasting the remaining dividends in the year.

            If the issuer is not a dividend payer or the dividend is
            suspended, NaN is returned.

            Input:
                years [Optional[int]]: past history length to use (min 2).
                    If None, all available data are used.
                mode [str]: mode of calculation. (Default "mean").

            Output:
                growth [float]: dividend growth
        """
        # Quick exit if not a dividends payer
        if (not self._is_div_payer) | self._is_div_suspended:
            return np.nan

        # Modes and quick exit on wrong calls
        modes = {'mean'}
        if mode not in modes:
            raise ValueError(f'DividendFactory.forecast(): mode {mode} not recognized')
        if years is not None:
            if years < 2:
                raise ValueError(f'DividendFactory.growth(): at least 2 years of history needed ({years} given)')

        growth = np.nan
        if mode == 'mean':
            growth = self._calc_mean_growth(years)

        return growth

    @property
    def is_dividend_payer(self) -> bool:
        return self._is_div_payer

    @property
    def is_dividend_suspended(self) -> bool:
        return self._is_div_suspended

    @property
    def last(self) -> tuple[np.datetime64 | None, float]:
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

    def ttm_div(self) -> float | None:
        """ Computes the TTM dividend. If the issuer is not a dividend payer, or
            the dividend is suspended zero is returned. The TTM are identified
            by the current t0 of the calendar.

            Output:
                div [float]: dividend TTM
        """
        if not self._is_div_payer:
            return None

        start = self._t0 - np.timedelta64(Cn.DAYS_IN_1Y, 'D')
        slc = search_trim_pos(self._div_dt, start)
        return float(np.sum(self._div[slc]))

    def ttm_yield(self) -> float | None:
        """ Computes the TTM dividend yield. If the issuer is not a dividend
            payer, or the dividend is suspended zero is returned. The TTM are
            identified by the current t0 of the calendar.

            Output:
                yield [float]: dividend yield TTM
        """
        if not self._is_div_payer:
            return None

        start = self._t0 - np.timedelta64(Cn.DAYS_IN_1Y, 'D')

        prices = self._eq.series('Price.SplitAdj.Close')
        p = prices.values
        p_dt = prices.index.values

        slc_d = search_trim_pos(self._div_dt, start)
        slc_p = search_trim_pos(p_dt, start, self._t0)

        return np.sum(self._div[slc_d]) / np.nanmean(p[slc_p])

    def ytd_div(self) -> float | None:
        """ Computes the YTD dividend. If the issuer is not a dividend payer, or
            the dividend is suspended zero is returned. The year of the YTD is
            identified by the current t0 of the calendar.

            Output:
                div [float]: dividend YTD
        """
        if not self._is_div_payer:
            return None

        start = np.datetime64(str(self._t0.astype('datetime64[Y]')) + '-01-01')
        slc = search_trim_pos(self._div_dt, start)
        return float(np.sum(self._div[slc]))

    def ytd_yield(self) -> float | None:
        """ Computes the YTD dividend yield. If the issuer is not a dividend
            payer, or the dividend is suspended zero is returned. The year of
            the YTD is identified by the current t0 of the calendar.

            Output:
                yield [float]: dividend yield YTD
        """
        if not self._is_div_payer:
            return None

        start = np.datetime64(str(self._t0.astype('datetime64[Y]')) + '-01-01')

        prices = self._eq.series('Price.SplitAdj.Close')
        p = prices.values
        p_dt = prices.index.values

        slc_d = search_trim_pos(self._div_dt, start)
        slc_p = search_trim_pos(p_dt, start, self._t0)

        return np.sum(self._div[slc_d]) / np.nanmean(p[slc_p])
