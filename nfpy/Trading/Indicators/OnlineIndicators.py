#
# Indicator functions
# Functions to compute indicators on time series. The output is a time series
# for the indicator.
#

from abc import abstractmethod
from bisect import bisect_left
from collections import deque

import numpy as np
from typing import Optional

from .Utils import (_check_len, _check_nans)


class BaseOnlineIndicator(object):

    def __init__(self, v: np.ndarray, w: int):
        self._v = v
        self._w = w

        self._i = 0
        self._max = v.shape[0]
        self._res = None

        _check_nans(v)
        _check_len(v, w)

    @abstractmethod
    def start(self, i: int) -> None:
        """ Precalculate enough to start the indicator. In case we want to start
            from the fist useful datapoint (the 10th for a 10 wide rolling
            window) we need to precalculate the initial part of the moving
            average.
        """

    def __iter__(self):
        return self

    @abstractmethod
    def __next__(self) -> tuple:
        """ Instruction to calculate next point. """


class Sma(BaseOnlineIndicator):

    def start(self, i: int) -> None:
        w = self._w
        if i < w - 1:
            raise ValueError(f'The start at {i} is too early, the minimum is {w - 1}')
        else:
            self._i = i
            self._res = np.mean(self._v[i - w + 1:i + 1])

    def __iter__(self):
        return self

    def __next__(self) -> tuple:
        i = self._i
        ma = self._res
        if i < self._max - 1:
            self._i += 1
            self._res += (self._v[self._i] - self._v[self._i - self._w]) / self._w
            return i, ma
        elif i == self._max - 1:
            self._i += 1
            return i, ma
        else:
            raise StopIteration


class Smstd(BaseOnlineIndicator):

    def __init__(self, v: np.ndarray, w: int, ddof: Optional[int] = 1):
        super().__init__(v, w)
        self._ddof = ddof
        self._ma = None

    def start(self, i: int) -> None:
        w = self._w
        if i < w - 1:
            raise ValueError(f'The start at {i} is too early, the minimum is {w - 1}')
        else:
            self._i = i
            self._ma = np.mean(self._v[i - w + 1:i + 1])
            self._res = np.std(self._v[i - w + 1:i + 1], ddof=self._ddof) ** 2

    def __iter__(self):
        return self

    def __next__(self) -> tuple:
        i = self._i
        std, ma = self._res, self._ma
        v, w = self._v, self._w
        if i < self._max - 1:
            self._i += 1
            diff = v[self._i] - v[self._i - w]
            self._ma += diff / w
            self._res += diff * (v[self._i] + v[self._i - w] - self._ma - ma) / \
                         (w - self._ddof)
            return i, np.sqrt(std)
        elif i == self._max - 1:
            self._i += 1
            return i, np.sqrt(std)
        else:
            raise StopIteration


class Csma(BaseOnlineIndicator):

    def __init__(self, v: np.ndarray):
        super().__init__(v, 0)
        self._msum = None

    def start(self, i: int) -> None:
        if i < 0:
            raise ValueError(f'The start at {i} is too early, the minimum is {0}')
        else:
            self._i = i
            self._msum = np.sum(self._v[:i + 1])
            self._res = self._msum / (i + 1)

    def __iter__(self):
        return self

    def __next__(self) -> tuple:
        i = self._i
        ma = self._res
        if i < self._max - 1:
            self._i += 1
            self._msum += self._v[self._i]
            self._res = self._msum / (self._i + 1)
            return i, ma
        elif i == self._max - 1:
            self._i += 1
            return i, ma
        else:
            raise StopIteration


class Ewma(BaseOnlineIndicator):

    def __init__(self, v: np.ndarray, w: int):
        super().__init__(v, w)
        self._al = 2. / (1. + w)
        self._c = 1. - self._al

    def start(self, i: int) -> None:
        if i < 0:
            raise ValueError(f'The start at {i} is too early, the minimum is {0}')
        else:
            self._i = i
            self._res = self._v[i]

    def __iter__(self):
        return self

    def __next__(self) -> tuple:
        i = self._i
        ma = self._res
        if i < self._max - 1:
            self._i += 1
            self._res = self._v[self._i] * self._al + ma * self._c
            return i, ma
        elif i == self._max - 1:
            self._i += 1
            return i, ma
        else:
            raise StopIteration


class Smd(BaseOnlineIndicator):

    def __init__(self, v: np.ndarray, w: int):
        super().__init__(v, w)
        self._elm = deque()
        self._idx = deque()
        self._is_even = False
        self._get = None
        self._mid = None

    def _get_odd(self) -> float:
        return self._elm[self._mid]

    def _get_even(self) -> float:
        return .5 * (self._elm[self._mid] + self._elm[self._mid - 1])

    def start(self, i: int) -> None:
        w = self._w
        if i < w - 1:
            raise ValueError(f'The start at {i} is too early, the minimum is {w - 1}')
        else:
            self._i = i
            self._mid = self._w // 2
            self._is_even = self._w % 2 == 0
            self._get = self._get_even if self._is_even else self._get_odd

            v = self._v[i - w + 1:i + 1]
            srt = np.argsort(v)
            val = np.take_along_axis(v, srt, axis=0)
            srt = np.argsort(srt)
            for i in range(len(srt)):
                self._idx.append(srt[i])
                self._elm.append(val[i])

            self._res = self._get()

    def __iter__(self):
        return self

    def __next__(self) -> tuple:
        i, med = self._i, self._res
        if i < self._max - 1:
            self._i += 1
            # Remove oldest observation from the window and update the indices
            old = self._idx.popleft()
            self._elm.remove(self._elm[old])
            for j, idx in enumerate(self._idx):
                if idx > old:
                    self._idx[j] = idx - 1

            # Add new observation to the window and update the indices
            new = self._v[self._i]
            ins_idx = bisect_left(self._elm, new)
            self._elm.insert(ins_idx, new)
            for j, idx in enumerate(self._idx):
                if idx >= ins_idx:
                    self._idx[j] = idx + 1
            self._idx.append(ins_idx)

            # Calculate the median
            self._res = self._get()
            return i, med
        elif i == self._max - 1:
            self._i += 1
            return i, med
        else:
            raise StopIteration


class Bollinger(BaseOnlineIndicator):

    def __init__(self, v: np.ndarray, w: int, alpha: float):
        super().__init__(v, w)
        self._a = alpha
        self._ma = Sma(v, w)
        self._std = Smstd(v, w)

    def start(self, i: int) -> None:
        w = self._w
        if i < w - 1:
            raise ValueError(f'The start at {i} is too early, the minimum is {w - 1}')
        else:
            self._i = i
            self._ma.start(i)
            self._std.start(i)
            ma = next(self._ma)[1]
            std = next(self._std)[1]

            band_dev = self._a * std
            low = ma - band_dev
            up = ma + band_dev
            bdiff = up - low
            bp = (self._v[i] - low) / bdiff
            bwidth = bdiff / ma

            self._res = (low, ma, up, bp, bwidth)

    def __iter__(self):
        return self

    def __next__(self) -> tuple:
        i, bol = self._i, self._res
        if i < self._max - 1:
            self._i += 1
            ma = next(self._ma)[1]
            std = next(self._std)[1]

            # Calculate bands
            band_dev = self._a * std
            low = ma - band_dev
            up = ma + band_dev
            bdiff = up - low
            bp = (self._v[i] - low) / bdiff
            bwidth = bdiff / ma

            self._res = (low, ma, up, bp, bwidth)
            return i, bol
        elif i == self._max - 1:
            self._i += 1
            return i, bol
        else:
            raise StopIteration


class Macd(BaseOnlineIndicator):

    def __init__(self, v: np.ndarray, w_slow: int, w_fast: int, w_macd: int):
        super().__init__(v, 0)
        self._sma = Ewma(v, w_slow)
        self._fma = Ewma(v, w_fast)
        self._al = 2. / (1. + w_macd)
        self._c = 1. - self._al
        self._signal = None

        if w_fast > w_slow:
            w_fast, w_slow = w_slow, w_fast
        elif w_fast == w_slow:
            raise ValueError('Windows for MACD cannot be equal')
        if w_macd >= w_fast:
            raise ValueError('MACD window should be smaller than fast EMA window')

    def start(self, i: int) -> None:
        if i < self._w:
            raise ValueError(f'The start at {i} is too early, the minimum is {self._w}')
        else:
            self._i = i
            self._sma.start(i)
            self._fma.start(i)

            sma = next(self._sma)[1]
            fma = next(self._fma)[1]
            macd = fma - sma

            self._res = (macd, macd, 0., fma, sma)

    def __iter__(self):
        return self

    def __next__(self) -> tuple:
        i, res = self._i, self._res
        if i < self._max - 1:
            self._i += 1
            sma = next(self._sma)[1]
            fma = next(self._fma)[1]
            macd = fma - sma

            signal = macd * self._al + self._c * res[1]
            hist = macd - signal

            self._res = (macd, signal, hist, fma, sma)
            return i, res
        elif i == self._max - 1:
            self._i += 1
            return i, res
        else:
            raise StopIteration
