#
# Dividends factory class
# Methods to deal with dividends
#

import numpy as np
import pandas as pd
from typing import Union

import nfpy.Calendar as Cal
from nfpy.Tools import (Constants as Cn)

from .Math import (compound, trim_ts, ts_yield)


class DividendFactory(object):
    _DAYS = np.array([30, 90, 180, 365])
    _FREQ = np.array([.08333, .25, .5, 1.])

    def __init__(self, eq, start: pd.Timestamp = None,
                 end: pd.Timestamp = None, tol: float = .5):
        # Input
        self._eq = eq
        self._start = Cal.pd_2_np64(start)
        self._t0 = Cal.pd_2_np64(end)
        self._tol = tol

        # Working variables
        self._div = None
        self._dt = None
        self._div_special = None
        self._dt_special = None
        self._num = None
        self._flim = None
        self._dist = None

        # Results
        self._divret = None
        self._daily_drift = None
        self._ann_drift = None
        self._freq = None
        self._days = None

        self._initialize()

    def __len__(self) -> int:
        return self._num

    @property
    def dividends(self) -> pd.Series:
        return pd.Series(self._div, index=self._dt)

    @property
    def dividends_special(self) -> Union[pd.Series, None]:
        if self._div_special is None:
            self._initialize_special_div()
        if self._div_special.shape[0] == 0:
            return None
        else:
            return pd.Series(self._div_special, index=self._dt_special)

    @property
    def num(self) -> int:
        return self.__len__()

    @property
    def frequency(self) -> float:
        if not self._freq:
            self._calc_freq()
        return self._freq

    @property
    def days(self) -> int:
        if not self._days:
            self._calc_freq()
        return self._days

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
    def last(self) -> []:
        return self._dt[-1], self._div[-1]

    def _initialize(self) -> None:
        """ Initialize the factory. """
        if self._tol > 1. or self._tol < 0.:
            msg = f'Tolerance for dividends should be in [0, 1], given {self._tol}'
            raise ValueError(msg)

        div = self._eq.dividends
        ts, dt = trim_ts(div.values, div.index.values, self._start, self._t0)
        self._num = ts.shape[0]
        self._div = ts
        self._dt = dt

    def _initialize_special_div(self) -> None:
        """ Initialize special dividends. This operation is not part of the
            standard initialization. Special dividends are evaluated lazyLY.
        """
        div = self._eq.dividends_special
        ts, dt = trim_ts(div.values, div.index.values, self._start, self._t0)
        self._div_special = ts
        self._dt_special = dt

    def dyield(self, date: pd.Timestamp = None) -> float:
        """ Compute the dividend yield at given date.

            Inputs:
                date [pd.Timestamp]: compute date (default None)

            Output:
                yield [float]: dividend yield
        """
        return ts_yield(
            self._dt, self._div,
            self._eq.prices.values,
            Cal.pd_2_np64(date)
        )

    def _calc_freq(self) -> None:
        """ Determine the frequency of dividends. The frequency is determined if
            dividends are a constant number of days apart from each other given
            a confidence interval. Note that special dividends issued in random
            days will prevent the determination of the dividend frequency.
        """
        if self._num < 2:
            msg = f'Too few dividends to determine dividend frequency in {self._eq.uid}'
            raise ValueError(msg)

        idx = np.argmin(
            np.abs(
                self._DAYS - np.quantile(self.distance, .75)
            )
        )
        self._freq = self._FREQ[idx]
        self._days = self._DAYS[idx]

    def _calc_drift(self) -> None:
        """ Determine the drift of dividends. """
        if self._num < 2:
            msg = f'Too few dividends to determine dividend drift in {self._eq.uid}'
            raise ValueError(msg)

        returns, distance = self.returns, self.distance
        self._daily_drift = np.mean(
            compound(returns, 1. / distance)
        )
        self._ann_drift = np.mean(
            compound(returns, Cn.BDAYS_IN_1Y / distance)
        )

    def _calc_returns(self) -> None:
        """ Calculates the percentage change of dividends. """
        if self._num < 2:
            msg = f'Too few dividends to determine dividend returns in {self._eq.uid}'
            raise ValueError(msg)
        self._divret = self._div[1:] / self._div[:-1] - 1.

    def _calc_distance(self) -> None:
        """ Calculates the distance in days between paid dividends. """
        idx = self._dt
        self._dist = np.array([
            (idx[i + 1] - idx[i]).astype('timedelta64[D]').astype('int')
            for i in range(self._num - 1)
        ])

    def search_sp_div(self) -> []:
        """ Function to search for special dividends. Creates a grid of
            plausible dates when to pay a dividend given the inferred frequency.
            The distance between the actual payment date and the theoretical one
            determines whether a dividend is classified as potentially special.
        """
        dt = (self._dt - self._dt[0]).astype('timedelta64[D]').astype('int')
        days = self.frequency * 365.
        grid = np.round(dt / days) * days
        anomaly = 2 * np.abs(dt - grid) / days

        exp = - 10. * (anomaly - .5)
        prob = 1. / (1. + np.exp(exp))

        return (
            self._dt[prob > self._tol],
            self._div[prob > self._tol],
            prob
        )
