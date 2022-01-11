#
# Dividends factory class
# Methods to deal with dividends
#

import numpy as np
from typing import Union

import nfpy.Calendar as Cal
from nfpy.Math import compound
from nfpy.Tools import (Constants as Cn)


class DividendFactory(object):

    def __init__(self, eq, tolerance: float = .5, suspension: float = 1.):
        # INPUTS
        self._eq = eq
        self._tol = max(tolerance, .0)
        self._suspension = max(suspension, .0) + 1.

        # WORKING VARIABLES
        # Dividends
        self._is_div_payer = False
        self._is_div_suspended = False
        self._div = None
        self._dt = None
        self._num = None

        # Special dividends
        self._special_div = None
        self._special_dt = None

        # RESULTS
        # Derived quantities on regular dividends
        self._dist = None
        self._divret = None
        self._daily_drift = None
        self._ann_drift = None
        self._freq = None

        # Annualized dividend quantities
        self._yearly_div = None
        self._yearly_dt = None

        self._initialize()

    def _initialize(self) -> None:
        """ Initialize the factory. """
        if self._tol > 1. or self._tol < 0.:
            msg = f'Tolerance for dividends should be in [0, 1], given {self._tol}'
            raise ValueError(msg)

        # Initialize special dividends
        div = self._eq.dividends_special
        self._special_div = div.values
        self._special_dt = div.index.values.astype('datetime64[D]')

        # Initialize dividends
        div = self._eq.dividends
        self._div = div.values
        self._dt = div.index.values.astype('datetime64[D]')
        self._num = self._div.shape[0]
        self._is_div_payer = True if self._num > 0 else False

        if not self._is_div_payer:
            return

        # Calculate frequency
        self._yearly_dt, idx, counts = np.unique(
            self._dt.astype('datetime64[Y]').astype(int) + 1970,
            return_inverse=True,
            return_counts=True
        )
        self._freq = int(np.round(np.mean(counts)))

        # Calculate yearly dividend as a sum
        divs = np.zeros(self._yearly_dt.shape)
        for n, i in enumerate(idx):
            divs[i] += self._div[n]

        # Adjust the first and the last year using the inferred frequency
        if counts[0] != self._freq:
            divs[0] *= self._freq / counts[0]
        if counts[-1] != self._freq:
            divs[-1] *= self._freq / counts[-1]
        self._yearly_div = divs

        # Check whether dividend is likely to have been suspended
        t0 = Cal.get_calendar_glob().t0.asm8.astype('datetime64[D]')
        div_gap = (t0 - self._dt[-1]).astype(int)
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

    # FIXME: use only numpy
    @property
    def dividends(self) -> Union[tuple[np.ndarray, np.ndarray], None]:
        if not self._is_div_payer:
            return None
        else:
            return self._dt, self._div

    @property
    def dividends_special(self) -> Union[tuple[np.ndarray, np.ndarray], None]:
        if not self._is_div_payer:
            return None
        else:
            return self._special_dt, self._special_div

    @property
    def annual_dividends(self) -> Union[tuple[np.ndarray, np.ndarray], None]:
        if not self._is_div_payer:
            return None
        else:
            return self._yearly_dt, self._yearly_div

    @property
    def num(self) -> int:
        return self.__len__()

    @property
    def frequency(self) -> int:
        return self._freq

    @property
    def returns(self) -> np.array:
        if self._divret is None:
            self._calc_returns()
        return self._divret

    @property
    def distance(self) -> np.array:
        if self._dist is None:
            self._calc_distance()
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
        return self._dt[-1], self._div[-1]

    def div_yield(self, date: np.datetime64 = None) -> float:
        """ Compute the dividend yield as last dividend annualized over
            the current price.

            Inputs:
                date [np.datetime64]: compute date (default None)

            Output:
                yield [float]: dividend yield
        """
        if not date:
            date = Cal.get_calendar_glob().t0
        pos = np.searchsorted(self._dt, [date])[0]
        return self._div[pos] * self._freq / self._eq.last_price(date)

    def _calc_drift(self) -> None:
        """ Determine the drift of dividends. """
        if self._num < 2:
            msg = f'Too few dividends to determine dividend drift in {self._eq.uid}'
            raise ValueError(msg)

        ret = np.minimum(
            compound(self.returns, Cn.BDAYS_IN_1Y / self.distance),
            1.
        )
        returns = ret * (1. - .2 * ret * ret - .2 * np.abs(ret))
        self._ann_drift = np.mean(returns)
        self._daily_drift = compound(self._ann_drift, 1. / Cn.BDAYS_IN_1Y)

    def _calc_returns(self) -> None:
        """ Calculates the percentage change of dividends. """
        if self._num < 2:
            msg = f'Too few dividends to determine dividend returns in {self._eq.uid}'
            raise ValueError(msg)

        self._divret = self._div[1:] / self._div[:-1] - 1.

    def _calc_distance(self) -> None:
        """ Calculates the distance in days between paid dividends. """
        if self._num < 2:
            msg = f'No distance for a single dividend in {self._eq.uid}'
            raise ValueError(msg)

        idx = self._dt
        self._dist = np.array([
            (idx[i + 1] - idx[i]).astype('timedelta64[D]').astype('int')
            for i in range(self._num - 1)
        ])

    def search_sp_div(self) -> tuple:
        """ Function to search for special dividends. Creates a grid of
            plausible dates when to pay a dividend given the inferred frequency.
            The distance between the actual payment date and the theoretical one
            determines whether a dividend is classified as potentially special.
        """
        dt = (self._dt - self._dt[0]).astype('timedelta64[D]').astype('int')
        days = Cn.DAYS_IN_1Y / self.frequency
        grid = np.round(dt / days) * days
        anomaly = 2 * np.abs(dt - grid) / days

        exp = - 10. * (anomaly - .5)
        prob = 1. / (1. + np.exp(exp))

        return (
            self._dt[prob > self._tol],
            self._div[prob > self._tol],
            prob
        )
