#
# Dividends factory class
# Methods to deal with dividends
#

import numpy as np
import pandas as pd

from nfpy.Assets.Equity import Equity
from nfpy.Financial.Returns import compound
from nfpy.Tools.TSUtils import trim_ts, ts_yield, dropna
from nfpy.Tools.Constants import BDAYS_IN_1Y


class DividendFactory(object):

    def __init__(self, eq: Equity, start: pd.Timestamp = None,
                 end: pd.Timestamp = None, confidence: float = .1):
        # Input
        self._eq = eq
        self._start = start
        self._t0 = end

        # Working variables
        self._div = None
        self._dt = None
        self._num = None
        self._flim = None
        self._dist = None

        # Results
        self._divret = None
        self._daily_drift = None
        self._ann_drift = None
        self._freq = None

        self._initialize(confidence)

    def __len__(self) -> int:
        return self._num

    @property
    def dividends(self) -> pd.Series:
        return pd.Series(self._div, index=self._dt)

    @property
    def num(self) -> int:
        return self.__len__()

    @property
    def frequency(self) -> float:
        if not self._freq:
            self._calc_freq()
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
    def last(self) -> tuple:
        return self._dt[-1], self._div[-1]

    def _initialize(self, c: float):
        """ Initialize the factory. """
        eq = self._eq.dividends
        ts, dt = dropna(eq.values, eq.index.values)
        ts, dt = trim_ts(ts, dt, self._start, self._t0)
        self._num = ts.shape[0]
        self._div = ts
        self._dt = dt

        u, d = 1 + c, 1 - c
        self._flim = [int(365 * d), int(365 * u), int(180 * d),
                      int(180 * u), int(90 * d), int(90 * u)]

    def dyield(self, date: pd.Timestamp = None) -> float:
        """ Compute the dividend yield at given date.

            Inputs:
                date [pd.Timestamp]: compute date (default None)

            Output:
                yield [float]: dividend yield
        """
        return ts_yield(self._div, self._dt, self._eq.prices, date)

    def _calc_freq(self):
        """ Determine the frequency of dividends. The frequency is determined if
            dividends are a constant number of days apart from each other given a
            confidence interval. Note that special dividends issued in random days
            will prevent the determination of the dividend frequency.

            Input:
                confidence [float]: confidence expressed as percentage (default .1)

            Output:
                freq [float]: frequency in years
                freq_array [np.array]: distance in days between each pair of
                                       dividends
        """
        # FIXME: the function does not work if "special" dividends are distributed
        if self._num < 2:
            raise ValueError('Too few dividends to determine dividend frequency in {}'
                             .format(self._eq.uid))

        mean_dist = np.mean(self.distance)
        if self._flim[0] <= mean_dist <= self._flim[1]:
            freq = 1.
        elif self._flim[2] <= mean_dist <= self._flim[3]:
            freq = .5
        elif self._flim[4] <= mean_dist <= self._flim[5]:
            freq = .25
        else:
            raise ValueError('Impossible to determine dividend frequency in {}'
                             .format(self._eq.uid))
        self._freq = freq

    def _calc_drift(self):
        """ Determine the drift of dividends. """
        div, num = self._div, self._num
        if num < 2:
            raise ValueError('Too few dividends to determine dividend drift in {}'
                             .format(self._eq.uid))

        returns, distance = self.returns, self.distance
        daily_ret = compound(returns, 1. / distance)
        annualized_ret = compound(returns, BDAYS_IN_1Y / distance)
        self._daily_drift = np.mean(daily_ret)
        self._ann_drift = np.mean(annualized_ret)

    def _calc_returns(self):
        """ Calculates the percentage change of dividends. """
        if self._num < 2:
            raise ValueError('Too few dividends to determine dividend returns in {}'
                             .format(self._eq.uid))
        self._divret = self._div[1:] / self._div[:-1] - 1.

    def _calc_distance(self):
        """ Calculates the distance in days between paid dividends. """
        # idx = self._div.index
        idx = self._dt
        self._dist = np.array([
            (idx[i + 1] - idx[i]).astype('timedelta64[D]').astype('int')
            for i in range(self._num - 1)])
