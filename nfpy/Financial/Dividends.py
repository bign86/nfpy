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
        # Falgs
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
        self._freq = None

        # Annualized dividend quantities
        self._yearly_div = np.array([])
        self._yearly_dt = np.array([])

        self._initialize()

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
        self._div_dt = div.index.values[slc]  # .astype('datetime64[D]')

        self._num = len(self._div)
        self._is_div_payer = True if self._num > 0 else False

        if not self._is_div_payer:
            return

        if self._num > 1:
            self._dist = np.diff(self._div_dt)

        # Calculate frequency
        self._yearly_dt, idx, counts = np.unique(
            self._div_dt.astype('datetime64[Y]'),  # .astype(int) + 1970,
            return_inverse=True,
            return_counts=True
        )
        self._freq = int(np.round(np.mean(counts)))

        # Calculate yearly dividend as a sum
        divs = np.zeros(self._yearly_dt.shape)
        for n, i in enumerate(idx):
            divs[i] += self._div[n]

        # Adjust the first and the last year using the inferred frequency
        divs[0] *= self._freq / counts[0]
        divs[-1] *= self._freq / counts[-1]
        self._yearly_div = divs

        # Check whether dividend is likely to have been suspended
        t0 = Cal.get_calendar_glob().t0.asm8.astype('datetime64[D]')
        div_gap = (t0 - self._div_dt[-1]).astype(int)
        limit = Cn.DAYS_IN_1Y * self._suspension / self.frequency
        if div_gap > limit:
            self._is_div_suspended = True

    def __len__(self) -> int:
        return self._num

    @property
    def is_dividend_payer(self) -> bool:
        return self._is_div_payer

    @property
    def is_dividend_suspended(self) -> bool:
        return self._is_div_suspended

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

    @property
    def annual_dividends(self) -> tuple[np.ndarray, np.ndarray]:
        return self._yearly_dt, self._yearly_div

    @property
    def num(self) -> int:
        return self.__len__()

    @property
    def frequency(self) -> int:
        return self._freq

    @property
    def distance(self) -> Optional[np.array]:
        return self._dist

    @property
    def drift(self) -> float:
        if self._daily_drift is None:
            self._calc_drift()
        return self._daily_drift

    @property
    def annualized_drift(self) -> float:
        if self._ann_drift is None:
            self._calc_drift()
        return self._ann_drift

    @property
    def last(self) -> tuple[np.datetime64, float]:
        return self._div_dt[-1], self._div[-1]

    def div_yield(self) -> tuple[np.ndarray, np.ndarray]:
        """ Compute the dividend yield as last dividend annualized over the
            current price.

            Output:
                year [np.ndarray]: series of years (Default None)
                yield [np.ndarray]: dividend yield for each year
        """
        prices = self._eq.prices
        p = prices.values
        p_dt = prices.index.values

        dt = np.r_[
            self._yearly_dt,
            np.datetime64(str(self._yearly_dt[-1] + 1) + '-01-01')
        ]
        idx = np.searchsorted(p_dt, dt)
        dy = np.empty(len(idx) - 1)

        for i in range(1, idx.shape[0]):
            dy[i - 1] = self._yearly_div[i - 1] / \
                        np.nanmean(p[idx[i - 1]:idx[i]])

        return self._yearly_dt, dy

    def trailing_yield(self) -> float:
        prices = self._eq.prices
        p = prices.values
        p_dt = prices.index.values

        dt = np.r_[
            self._yearly_dt[-1:],
            np.datetime64(str(self._yearly_dt[-1] + 1) + '-01-01')
        ]
        idx = np.searchsorted(p_dt, dt)
        # print(f'dividend: {self._yearly_div[-1]} @ {self._yearly_dt[-1]}')
        # print(f'prices from {p_dt[idx[0]]} to {p_dt[idx[1] + 1]}')

        return self._yearly_div[-1] / \
               np.nanmean(p[idx[0]:idx[1] + 1])

    def _calc_drift(self) -> None:
        """ Determine the drift of dividends. """
        if self._num < 2:
            msg = f'Too few dividends to determine dividend drift in {self._eq.uid}'
            raise ValueError(msg)

        ret = np.minimum(
            self._yearly_div[1:] / self._yearly_div[:-1] - 1.,
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

    def search_sp_div(self) -> tuple:
        """ Function to search for special dividends. Creates a grid of
            plausible dates when to pay a dividend given the inferred frequency.
            The distance between the actual payment date and the theoretical one
            determines whether a dividend is classified as potentially special.
        """
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
