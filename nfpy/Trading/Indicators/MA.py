#
# Moving Average Indicators
# Moving Average based indicators.
#

import numpy as np
from typing import Union

import nfpy.Math as Math

from .BaseIndicator import BaseIndicator


class Sma(BaseIndicator):
    """ Simple Moving Average indicator. """

    _NAME = 'sma'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._ma = None

        super(Sma, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._ma = np.empty(self._max_t, dtype=float)
        self._ma[:self._w - 1] = np.nan

        end = None if self._is_bulk else t0 + 1
        ma_slc = slice(self._w - 1, end)
        ts_slc = slice(None, end)

        self._ma[ma_slc] = Math.rolling_mean(self._ts[ts_slc], self._w)

    def get_indicator(self) -> dict:
        return {'sma': self._ma}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._ma[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        ma = self._ma[self._t - 1] + (self._ts[self._t] - self._ts[self._t - self._w]) / self._w
        self._ma[self._t] = ma
        return ma

    @property
    def min_length(self) -> int:
        return self._w


class Smstd(BaseIndicator):
    """ Simple Moving Standard Deviation indicator. """

    _NAME = 'smstd'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int, ddof: int = 1):
        self._w = w
        self._dof = ddof
        self._std = None

        super(Smstd, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._std = np.empty(self._max_t, dtype=float)
        self._std[:self._w - 1] = np.nan

        if self._is_bulk:
            std_slc = slice(self._w - 1, None)
            ts_slc = slice(None, None)
        else:
            std_slc = slice(self._w - 1, t0 + 1)
            ts_slc = slice(None, t0 + 1)

        ts2d = Math.rolling_window(self._ts[ts_slc], self._w)
        self._std[std_slc] = np.std(ts2d, axis=1, ddof=self._dof)

    def get_indicator(self) -> dict:
        return {'smstd': self._std}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._std[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        std = np.std(self._ts[self._t - self._w + 1:self._t + 1], axis=0, ddof=self._dof)
        self._std[self._t] = std
        return float(std)

    @property
    def min_length(self) -> int:
        return self._w


class Csma(BaseIndicator):
    """ Cumulative Simple Moving Average indicator. """

    _NAME = 'csma'

    def __init__(self, ts: np.ndarray, is_bulk: bool):
        self._ma = None
        self._sum = .0
        self._count = 0

        super(Csma, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._ma = np.empty(self._max_t, dtype=float)

        if self._is_bulk:
            slc = slice(None, None)
        else:
            slc = slice(None, t0 + 1)

        _sum = np.nancumsum(self._ts[slc])
        _div = np.array(
            range(
                self._ts[slc].shape[self._ts.ndim - 1]
            )
        ) + 1
        self._ma[slc] = _sum / _div

        self._sum = float(_sum[-1])
        self._count = int(_div[-1])

    def get_indicator(self) -> dict:
        return {'csma': self._ma}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._ma[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        self._sum += self._ts[self._t]
        self._count += 1
        cma = self._sum / self._count
        self._ma[self._t] = cma
        return cma

    @property
    def min_length(self) -> int:
        return 1


class Ewma(BaseIndicator):
    """ Exponentially Weighted Moving Average indicator. """

    _NAME = 'ewma'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._ma = None
        self._w = w
        self._alpha = 2. / (1. + w)
        self._c = 1. - self._alpha

        super(Ewma, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._ma = np.empty(self._max_t, dtype=float)

        self._ma[0] = self._ts[0]
        end = self._max_t if self._is_bulk else t0 + 1
        for i in range(1, end):
            self._ma[i] = self._alpha * self._ts[i] + self._c * self._ma[i - 1]

    def get_indicator(self) -> dict:
        return {'ewma': self._ma}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._ma[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        new = self._alpha * self._ts[self._t] + self._c * self._ma[self._t - 1]
        self._ma[self._t] = new
        return new

    @property
    def min_length(self) -> int:
        return self._w


class Smd(BaseIndicator):
    """ Simple Moving Median indicator. """

    _NAME = 'smd'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._smd = None

        super(Smd, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._smd = np.empty(self._max_t, dtype=float)
        self._smd[:self._w - 1] = np.nan

        if self._is_bulk:
            std_slc = slice(self._w - 1, None)
            ts_slc = slice(None, None)
        else:
            std_slc = slice(self._w - 1, t0 + 1)
            ts_slc = slice(None, t0 + 1)

        ts2d = Math.rolling_window(self._ts[ts_slc], self._w)
        self._smd[std_slc] = np.median(ts2d, axis=1)

    def get_indicator(self) -> dict:
        return {'smd': self._smd}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._smd[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        smd = np.median(self._ts[self._t - self._w + 1:self._t + 1], axis=0)
        self._smd[self._t] = smd
        return float(smd)

    @property
    def min_length(self) -> int:
        return self._w


class Macd(BaseIndicator):
    """ Moving Average Convergence Divergence indicator. """

    _NAME = 'macd'

    def __init__(self, ts: np.ndarray, is_bulk: bool, ws: int, wf: int, wm: int):
        self._ws = ws
        self._wf = wf
        self._wm = wm
        self._als = 2. / (1. + ws)
        self._alf = 2. / (1. + wf)
        self._alm = 2. / (1. + wm)
        self._cs = 1. - self._als
        self._cf = 1. - self._alf
        self._cm = 1. - self._alm

        self._mas = .0
        self._maf = .0
        self._macd = None
        self._signal = None
        self._hist = None

        super(Macd, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._macd = np.empty(self._max_t, dtype=float)
        self._signal = np.empty(self._max_t, dtype=float)
        self._hist = np.empty(self._max_t, dtype=float)

        self._mas = self._ts[0]
        self._maf = self._ts[0]
        self._macd[0] = .0
        self._signal[0] = .0
        self._hist[0] = .0

        end = self._max_t if self._is_bulk else t0 + 1
        for i in range(1, end):
            self._mas = self._als * self._ts[i] + self._cs * self._mas
            self._maf = self._alf * self._ts[i] + self._cf * self._maf
            self._macd[i] = self._maf - self._mas
            self._signal[i] = self._alm * self._macd[i] + self._cm * self._signal[i - 1]
        self._hist[1:end] = self._macd[1:end] - self._signal[1:end]

    def get_indicator(self) -> dict:
        return {'macd': self._macd, 'signal': self._signal, 'hist': self._hist}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._macd[self._t], self._signal[self._t], self._hist[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        self._mas = self._als * self._ts[self._t] + self._cs * self._mas
        self._maf = self._alf * self._ts[self._t] + self._cf * self._maf
        macd = self._maf - self._mas
        signal = self._alm * macd + self._cm * self._signal[self._t - 1]
        hist = macd - signal
        self._macd[self._t] = macd
        self._signal[self._t] = signal
        self._hist[self._t] = hist
        return macd, signal, hist

    @property
    def min_length(self) -> int:
        return self._ws + self._wm - 1


class Dema(BaseIndicator):
    """ Double Exponential Moving Average indicator. """

    _NAME = 'dema'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._alpha = 2. / (1. + w)
        self._c = 1. - self._alpha

        self._dema = None
        self._ma1 = .0
        self._ma2 = .0

        super(Dema, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._dema = np.empty(self._max_t, dtype=float)

        self._ma1 = self._ts[0]
        self._ma2 = self._ts[0]
        self._dema[0] = self._ts[0]

        end = self._max_t if self._is_bulk else t0 + 1
        for i in range(1, end):
            self._ma1 = self._alpha * self._ts[i] + self._c * self._ma1
            self._ma2 = self._alpha * self._ma1 + self._c * self._ma2
            self._dema[i] = 2. * self._ma1 - self._ma2

    def get_indicator(self) -> dict:
        return {'dema': self._dema}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._dema[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        self._ma1 = self._alpha * self._ts[self._t] + self._c * self._ma1
        self._ma2 = self._alpha * self._ma1 + self._c * self._ma2
        dema = 2. * self._ma1 - self._ma2
        self._dema[self._t] = dema
        return dema

    @property
    def min_length(self) -> int:
        return self._w


class Tema(BaseIndicator):
    """ Triple Exponential Moving Average indicator. """

    _NAME = 'tema'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._alpha = 2. / (1. + w)
        self._c = 1. - self._alpha

        self._tema = None
        self._ma1 = .0
        self._ma2 = .0
        self._ma3 = .0

        super(Tema, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._tema = np.empty(self._max_t, dtype=float)

        self._ma1 = self._ts[0]
        self._ma2 = self._ts[0]
        self._ma3 = self._ts[0]
        self._tema[0] = self._ts[0]

        end = self._max_t if self._is_bulk else t0 + 1
        for i in range(1, end):
            self._ma1 = self._alpha * self._ts[i] + self._c * self._ma1
            self._ma2 = self._alpha * self._ma1 + self._c * self._ma2
            self._ma3 = self._alpha * self._ma2 + self._c * self._ma3
            self._tema[i] = 3. * self._ma1 - 3. * self._ma2 + self._ma3

    def get_indicator(self) -> dict:
        return {'tema': self._tema}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._tema[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        self._ma1 = self._alpha * self._ts[self._t] + self._c * self._ma1
        self._ma2 = self._alpha * self._ma1 + self._c * self._ma2
        self._ma3 = self._alpha * self._ma2 + self._c * self._ma3
        tema = 3. * self._ma1 - 3. * self._ma2 + self._ma3
        self._tema[self._t] = tema
        return tema

    @property
    def min_length(self) -> int:
        return self._w


class Alma(BaseIndicator):
    """ Arnaud Legoux Moving Average indicator. """

    _NAME = 'alma'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int,
                 offset: float = .85, vola: float = 6.):
        self._w = w
        self._offset = offset * (w - 1)
        self._vola = 2. * w * w / vola / vola
        self._ma = None

        self._factor = np.exp(
            -(np.arange(self._w) - self._offset) ** 2. / self._vola
        )
        self._norm = np.sum(self._factor)

        super(Alma, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._ma = np.empty(self._max_t, dtype=float)
        self._ma[:self._w - 1] = np.nan

        if self._is_bulk:
            ma_slc = slice(self._w - 1, None)
            ts_slc = slice(None, None)
        else:
            ma_slc = slice(self._w - 1, t0 + 1)
            ts_slc = slice(None, t0 + 1)

        roll = Math.rolling_window(self._ts[ts_slc], self._w)
        self._ma[ma_slc] = np.sum(roll * self._factor, axis=1) / self._norm

    def get_indicator(self) -> dict:
        return {'alma': self._ma}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._ma[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        ma = np.sum(self._ts[self._t - self._w + 1:self._t + 1] * self._factor) / self._norm
        self._ma[self._t] = ma
        return ma

    @property
    def min_length(self) -> int:
        return self._w



