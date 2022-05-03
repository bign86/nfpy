#
# Dividends factory class
# Methods to deal with dividends
#

import numpy as np
from typing import Optional

from nfpy.Assets import TyAsset
import nfpy.Calendar as Cal
from nfpy.Math import (compound, search_trim_pos)
from nfpy.Tools import (Constants as Cn)


class DividendFactory(object):

    def __init__(self, eq: TyAsset, tolerance: float = .5, suspension: float = 1.):
        # INPUTS
        self._eq = eq
        self._tol = max(tolerance, .0)
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
        self._daily_drift = None
        self._ann_drift = None
        self._freq = 0

        # Annualized dividend quantities
        self._yearly_div = np.array([])
        self._yearly_dt = np.array([])

        self._initialize()

    def _calc_drift(self) -> None:
        """ Calculates the drift of dividends both daily and annual. """
        if self._num < 2:
            msg = f'Too few dividends to determine dividend drift in {self._eq.uid}'
            raise ValueError(msg)

        # The current year is excluded from the calculation
        ret = np.minimum(
            self._yearly_div[1:-1] / self._yearly_div[:-2] - 1.,
            1.
        )
        returns = ret * (1. - .2 * ret * ret - .2 * np.abs(ret))
        # print(f'_calc_drift()\nret: {ret}\nadj: {returns}')

        self._ann_drift = np.mean(returns)
        self._daily_drift = compound(self._ann_drift, 1. / Cn.BDAYS_IN_1Y)

    def _calc_returns(self) -> None:
        """ Calculates the percentage change of dividends. """
        if self._num < 2:
            msg = f'Too few dividends to determine dividend returns in {self._eq.uid}'
            raise ValueError(msg)

        self._divret = self._div[1:] / self._div[:-1] - 1.

    def _initialize(self) -> None:
        """ Initialize the factory. """
        if self._eq.type != 'Equity':
            msg = f'DividendFactory() supports only equities not {self._eq.type}'
            raise ValueError(msg)

        if self._tol > 1. or self._tol < 0.:
            msg = f'Tolerance for dividends should be in [0, 1], given {self._tol}'
            raise ValueError(msg)

        # Initialize dividends stopping at t0
        div = self._eq.dividends
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
        self._freq = int(np.round(np.mean(counts)))

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
        for n, i in enumerate(years_idx[:-1]):
            divs[n] += np.sum(self._div[i:i + 1])

        # Adjust the first year using the inferred frequency
        divs[0] *= self._freq / counts[0]
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

    @property
    def annualized_drift(self) -> float:
        """ Returns the annual drift of dividends calculated from the annual
            series. The result is YTD for the current year. If the issuer is not
            a dividend payer or the dividend is suspended, .0 is returned.
        """
        if (not self._is_div_payer) | self._is_div_suspended:
            return .0
        if self._ann_drift is None:
            self._calc_drift()
        return self._ann_drift

    @property
    def distance(self) -> np.array:
        return self._dist

    @property
    def dividends(self) -> tuple[np.ndarray, np.ndarray]:
        return self._div_dt, self._div

    @property
    def dividends_special(self) -> tuple[np.ndarray, np.ndarray]:
        return (
            self._eq.dividends_special.values,
            self._eq.dividends_special.index
                .values
                .astype('datetime64[D]')
        )

    def div_yields(self) -> tuple[np.ndarray, np.ndarray]:
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

        prices = self._eq.prices

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
    def drift(self) -> float:
        """ Returns the daily drift of dividends calculated from the dividend
            series. If the issuer is not a dividend payer or the dividend is
            suspended, .0 is returned.
        """
        if (not self._is_div_payer) | self._is_div_suspended:
            return .0
        if self._daily_drift is None:
            self._calc_drift()
        return self._daily_drift

    @property
    def frequency(self) -> int:
        return self._freq

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

    def search_sp_div(self) -> tuple:
        """ Function to search for special dividends. Creates a grid of
            plausible dates when to pay a dividend given the inferred frequency.
            The distance between the actual payment date and the theoretical one
            determines whether a dividend is classified as potentially special.
        """
        if not self._is_div_payer:
            return np.array([]), np.array([]), .0

        dt = (self._div_dt - self._div_dt[0]).astype('int')
        days = Cn.DAYS_IN_1Y / self.frequency
        grid = np.round(dt / days) * days
        anomaly = 2 * np.abs(dt - grid) / days

        exp = - 10. * (anomaly - .5)
        prob = 1. / (1. + np.exp(exp))

        return (
            self._div_dt[prob > self._tol],
            self._div[prob > self._tol],
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

        start = self._t0.astype('datetime64[Y]') - \
                np.timedelta64(Cn.DAYS_IN_1Y, 'D')
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

        start = self._t0.astype('datetime64[Y]') - \
                np.timedelta64(Cn.DAYS_IN_1Y, 'D')

        prices = self._eq.prices
        p = prices.values
        p_dt = prices.index.values

        idx_d = np.searchsorted(self._div_dt, start)
        idx_p = np.searchsorted(p_dt, start)

        return np.sum(self._div[idx_d:]) / np.nanmean(p[idx_p:])
