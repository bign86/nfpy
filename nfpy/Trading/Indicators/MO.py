#
# Momentum Oscillator Indicators
# Momentum Oscillator based indicators.
#

import numpy as np
from typing import Union

import nfpy.Math as Math

from .BaseIndicator import BaseIndicator


class Aroon(BaseIndicator):
    """ Calculates the Aroon bands and oscillator over the given window. The
        <ts> array is expected to have either shape (1, n) or shape (2, n) with
        each row having the structure:
            <high, low>.
    """

    _NAME = 'aroon'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._aro = None
        self._aro_up = None
        self._aro_dwn = None

        super(Aroon, self).__init__(ts, is_bulk)

    def _bulk(self, t0: int) -> None:
        self._aro = np.empty(self._max_t, dtype=float)
        self._aro_up = np.empty(self._max_t, dtype=float)
        self._aro_dwn = np.empty(self._max_t, dtype=float)

        self._aro[:self._w - 1] = np.nan
        self._aro_up[:self._w - 1] = np.nan
        self._aro_dwn[:self._w - 1] = np.nan

        # Calculate the Aroon over the relevant time period
        if self._is_bulk:
            ts_slc = slice(0, None)
            a_slc = slice(self._w - 1, None)
        else:
            ts_slc = slice(0, t0 + 1)
            a_slc = slice(self._w - 1, t0 + 1)

        roll = Math.rolling_window(self._ts[ts_slc], self._w)
        up = 100. * np.argmax(roll, axis=1) / self._w
        down = 100. * np.argmin(roll, axis=1) / self._w

        self._aro[a_slc] = up - down
        self._aro_up[a_slc] = up
        self._aro_dwn[a_slc] = down

    def get_indicator(self) -> dict:
        return {'up': self._aro_up, 'down': self._aro_dwn, 'aroon': self._aro}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._aro_up[self._t], self._aro_dwn[self._t], self._aro[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        slc = self._ts[self._t - self._w: self._t + 1]
        up = 100. * np.argmax(slc) / self._w
        down = 100. * np.argmin(slc) / self._w
        aroon = up - down

        self._aro[self._t] = aroon
        self._aro_up[self._t] = up
        self._aro_dwn[self._t] = down
        return up, down, aroon

    # NON-Vectorized version. Slower in Python, but closer to full C.
    # def _ind_online(self) -> Union[float, tuple]:
    #     if self._t - self._max[0] > self._w:
    #         t = min(self._t + 1, self._max_t)
    #         slc = self._ts[self._t - self._w: t]
    #         imax = np.argmax(slc)
    #         self._max = (imax, self._ts[imax])
    #         up = 100. * imax / self._w
    #
    #         imin = np.argmin(slc)
    #         self._min = (imin, self._ts[imin])
    #         down = 100. * imin / self._w
    #     else:
    #         # max
    #         if self._ts[self._t] > self._max[1]:
    #             self._max = (self._t, self._ts[self._t])
    #             up = 0
    #         else:
    #             up = 100. * self._max[0] / self._w
    #
    #         # min
    #         if self._ts[self._t] < self._min[1]:
    #             self._min = (self._t, self._ts[self._t])
    #             down = 0
    #         else:
    #             down = 100. * self._min[0] / self._w
    #
    #     aroon = up - down
    #
    #     self._aro[self._t] = aroon
    #     self._aro_up[self._t] = up
    #     self._aro_dwn[self._t] = down
    #     return up, down, aroon

    @property
    def min_length(self) -> int:
        return self._w


class Atr(BaseIndicator):
    """ Calculates the Average True Range over the given window. The <ts> array
        is expected to have shape (3, n) with each row having the structure:
            <high, low, close>.
        If an array with shape (n,) is provided, the normal volatility is
        calculated as a backup solution.
    """

    _NAME = 'atr'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._atr = None

        super(Atr, self).__init__(ts, is_bulk)

        if len(ts.shape) == 1:
            self._is_hlc = False
            if not self._is_bulk:
                setattr(self, '_ind', self._ind_c)
        elif (len(ts.shape) == 2) and (ts.shape[0] == 3):
            self._is_hlc = True
            if not self._is_bulk:
                setattr(self, '_ind', self._ind_hlc)
        else:
            raise ValueError(f"Indicator {self._NAME}: Input malformed: ts.shape != (n,) or (3, n)")

    def _bulk(self, t0: int) -> None:
        self._atr = np.empty(self._max_t, dtype=float)
        self._atr[:self._w] = np.nan

        # Calculate the TR over the relevant time period
        if self._is_hlc:
            if self._is_bulk:
                hl_slc = slice(1, None)
                c_slc = slice(0, -1)
            else:
                hl_slc = slice(1, t0 + 1)
                c_slc = slice(0, t0)
            tr = np.maximum(self._ts[0, hl_slc], self._ts[2, c_slc]) - \
                 np.minimum(self._ts[1, hl_slc], self._ts[2, c_slc])
        else:
            if self._is_bulk:
                hl_slc = slice(1, None)
                c_slc = slice(0, -1)
            else:
                hl_slc = slice(1, t0 + 1)
                c_slc = slice(0, t0)
            tr = np.abs(self._ts[hl_slc] - self._ts[c_slc])

        # Calculate the first point for the ATR using a simple average
        atr = np.mean(tr[:self._w + 1])
        self._atr[self._w] = atr

        # Calculate the remaining points as an exponential average
        # https://en.wikipedia.org/wiki/Average_true_range
        for i in range(self._w + 1, t0 + 1):
            atr = (atr * (self._w - 1) + tr[i - 1]) / self._w
            self._atr[i] = atr

    def get_indicator(self) -> dict:
        return {'atr': self._atr}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._atr[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        pass

    def _ind_c(self) -> float:
        tr = np.abs(self._ts[self._t] - self._ts[self._t - 1])
        atr = (self._atr[self._t - 1] * (self._w - 1) + tr) / self._w
        self._atr[self._t] = atr
        return atr

    def _ind_hlc(self) -> float:
        prev_close = self._ts[2, self._t - 1]
        tr = max(self._ts[0, self._t], prev_close) - \
             min(self._ts[1, self._t], prev_close)
        atr = (self._atr[self._t - 1] * (self._w - 1) + tr) / self._w
        self._atr[self._t] = atr
        return atr

    @property
    def min_length(self) -> int:
        return self._w + 1


class Cci(BaseIndicator):
    """ Calculates the Commodity Channel Index indicator. """

    _NAME = 'cci'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._cci = None
        self._dmean = None
        self._sma = .0
        self._mad = .0

        super(Cci, self).__init__(ts, is_bulk)

    def _bulk(self, t0: int) -> None:
        self._cci = np.empty(self._max_t, dtype=float)
        self._cci[:self._w - 1] = np.nan
        self._dmean = np.empty(self._max_t, dtype=float)

        if self._is_bulk:
            ma_slc = slice(None, None)
            cci_slc = slice(self._w - 1, None)
        else:
            ma_slc = slice(None, t0 + 1)
            cci_slc = slice(self._w - 1, t0 + 1)

        sma = Math.rolling_mean(self._ts[ma_slc], self._w)
        sma = np.r_[[sma[0]] * (self._w - 1), sma]
        self._dmean[ma_slc] = self._ts[ma_slc] - sma
        mad = Math.rolling_mean(np.abs(self._dmean[ma_slc]), self._w)
        self._sma = float(sma[-1])
        self._mad = float(mad[-1])

        self._cci[cci_slc] = self._dmean[cci_slc] / (.015 * mad)

    def get_indicator(self) -> dict:
        return {'cci': self._cci}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._cci[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        self._sma += (self._ts[self._t] - self._ts[self._t - self._w]) / self._w
        dmean = self._ts[self._t] - self._sma
        self._mad += (np.abs(dmean) - np.abs(self._dmean[self._t - self._w])) / self._w
        cci = dmean / (.015 * self._mad)
        self._dmean[self._t] = dmean
        self._cci[self._t] = cci
        return cci

    @property
    def min_length(self) -> int:
        return self._w


class Fi(BaseIndicator):
    """ Force Index indicator calculation. It is the price difference scaled by
        the trade volume. The input must have shape (2, n) and be like:
            <price, volume>.
    """

    _NAME = 'fi'

    def __init__(self, ts: np.ndarray, is_bulk: bool):
        self._fi = None

        if len(ts.shape) != 2:
            raise ValueError(f"Indicator {self._NAME}: Input malformed: ts.shape != (2,n)")

        super(Fi, self).__init__(ts, is_bulk)

    def _bulk(self, t0: int) -> None:
        self._fi = np.empty(self._max_t, dtype=float)

        if self._is_bulk:
            df_slc = slice(None, None)
            ts_slc = slice(1, None)
        else:
            df_slc = slice(None, t0 + 1)
            ts_slc = slice(1, t0 + 1)

        self._fi[df_slc] = np.r_[np.nan, np.diff(self._ts[0, df_slc]) * self._ts[1, ts_slc]]

    def get_indicator(self) -> dict:
        return {'fi': self._fi}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._fi[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        fi = (self._ts[0, self._t] - self._ts[0, self._t - 1]) * self._ts[1, self._t]
        self._fi[self._t] = fi
        return fi

    @property
    def min_length(self) -> int:
        return 2


class FiElder(BaseIndicator):
    """ Elder's Force Index indicator calculation. It is the moving average of
        the price difference scaled by the trade volume. The input must have
        shape (2, n) and be like:
            <price, volume>.
    """

    _NAME = 'fielder'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._fi = None
        self._fie = None

        if len(ts.shape) != 2:
            raise ValueError(f"Indicator {self._NAME}: Input malformed: ts.shape != (2,n)")

        super(FiElder, self).__init__(ts, is_bulk)

    def _bulk(self, t0: int) -> None:
        self._fi = np.empty(self._max_t, dtype=float)
        self._fie = np.empty(self._max_t, dtype=float)
        self._fie[:self._w - 1] = np.nan

        if self._is_bulk:
            df_slc = slice(None, None)
            ts_slc = slice(1, None)
            out_slc = slice(self._w - 1, None)
        else:
            df_slc = slice(None, t0 + 1)
            ts_slc = slice(1, t0 + 1)
            out_slc = slice(self._w - 1, t0 + 1)

        fi = np.r_[np.nan, np.diff(self._ts[0, df_slc]) * self._ts[1, ts_slc]]
        self._fi[df_slc] = fi
        self._fie[out_slc] = Math.rolling_mean(fi, self._w)

    def get_indicator(self) -> dict:
        return {'fielder': self._fie}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._fie[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        fi = (self._ts[0, self._t] - self._ts[0, self._t - 1]) * self._ts[1, self._t]
        fie = self._fie[self._t - 1] + (fi - self._fi[self._t - self._w]) / self._w
        self._fi[self._t] = fi
        self._fie[self._t] = fie
        return fie

    @property
    def min_length(self) -> int:
        return self._w


class Mfi(BaseIndicator):
    """ Money Flow Index indicator calculation. The <ts> array is expected to
        have a shape like (2, n) or (4, n) with structure:
            <close, volume> or <high, low, close, volume>.
    """

    _NAME = 'mfi'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._mfi = None
        self._pos_mf = None
        self._neg_mf = None
        self._roll_pos_mf = 0
        self._roll_neg_mf = 0

        if len(ts.shape) not in (2, 4):
            raise ValueError(f"Indicator {self._NAME}: Input malformed: ts.shape != (2,n) or (4,n)")

        if ts.shape[0] == 4:
            tp = np.sum(ts[:3, :], axis=1) / 3.
            ts = np.vstack(tp, ts[3, :])

        super(Mfi, self).__init__(ts, is_bulk)

    def _bulk(self, t0: int) -> None:
        self._mfi = np.empty(self._max_t, dtype=float)
        self._mfi[:self._w - 1] = np.nan
        self._pos_mf = np.empty(self._max_t, dtype=int)
        self._neg_mf = np.empty(self._max_t, dtype=int)

        if self._is_bulk:
            ts_slc = slice(None, None)
            mfi_slc = slice(self._w - 1, None)
        else:
            ts_slc = slice(None, t0 + 1)
            mfi_slc = slice(self._w - 1, t0 + 1)

        raw_money_flow = np.r_[
            np.nan,
            np.diff(self._ts[0, ts_slc] * self._ts[1, ts_slc])
        ]
        pos_mf = np.where(raw_money_flow > .0, 1, 0)
        neg_mf = np.where(raw_money_flow < .0, 1, 0)

        roll_pos_mf = Math.rolling_sum(pos_mf, self._w)
        roll_neg_mf = Math.rolling_sum(neg_mf, self._w)
        mf = roll_pos_mf / roll_neg_mf

        self._pos_mf[ts_slc] = pos_mf
        self._neg_mf[ts_slc] = neg_mf
        self._roll_pos_mf = roll_pos_mf[-1]
        self._roll_neg_mf = roll_neg_mf[-1]
        self._mfi[mfi_slc] = 100. - 100. / (1. + mf)

    def get_indicator(self) -> dict:
        return {'mfi': self._mfi}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._mfi[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        raw_money_flow = self._ts[0, self._t] * self._ts[1, self._t] - \
                         self._ts[0, self._t - 1] * self._ts[1, self._t - 1]
        self._pos_mf[self._t] = 1 if raw_money_flow > .0 else 0
        self._neg_mf[self._t] = 1 if raw_money_flow < .0 else 0

        self._roll_pos_mf += self._pos_mf[self._t] - self._pos_mf[self._t - self._w]
        self._roll_neg_mf += self._neg_mf[self._t] - self._neg_mf[self._t - self._w]

        mf = self._roll_pos_mf / self._roll_neg_mf
        mfi = 100. - 100. / (1. + mf)
        self._mfi[self._t] = mfi
        return mfi

    @property
    def min_length(self) -> int:
        return self._w


class RsiCutler(BaseIndicator):
    """ Cutler's Relative Strength Index indicator using the SMA. """

    _NAME = 'rsicutler'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._rsi = None
        self._up = None
        self._down = None
        self._ma_up = .0
        self._ma_down = .0

        super(RsiCutler, self).__init__(ts, is_bulk)

    def _bulk(self, t0: int) -> None:
        self._rsi = np.empty(self._max_t, dtype=float)
        self._rsi[:self._w - 1] = np.nan
        self._up = np.empty(self._max_t, dtype=float)
        self._down = np.empty(self._max_t, dtype=float)

        if self._is_bulk:
            slc = slice(None, None)
            rsi_slc = slice(self._w - 1, None)
        else:
            slc = slice(None, t0 + 1)
            rsi_slc = slice(self._w - 1, t0 + 1)

        up_d = np.r_[np.nan, np.diff(self._ts[slc])]
        down_d = -np.copy(up_d)
        up_d[up_d < 0.] = 0.
        down_d[down_d < 0.] = 0.

        ma_up = Math.rolling_mean(up_d, self._w)
        ma_down = Math.rolling_mean(down_d, self._w)
        rs = ma_up / ma_down

        self._up[slc] = up_d
        self._down[slc] = down_d
        self._ma_up = ma_up[-1]
        self._ma_down = ma_down[-1]
        self._rsi[rsi_slc] = 100. - 100. / (1. + rs)

    def get_indicator(self) -> dict:
        return {'rsi': self._rsi}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._rsi[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        up_d = self._ts[self._t] - self._ts[self._t - 1]
        down_d = 0. if up_d > 0. else -up_d
        up_d = 0. if up_d < 0. else up_d

        self._ma_up += (up_d - self._up[self._t - self._w]) / self._w
        self._ma_down += (down_d - self._down[self._t - self._w]) / self._w
        rs = self._ma_up / self._ma_down
        rsi = 100. - 100. / (1. + rs)

        self._up[self._t] = up_d
        self._down[self._t] = down_d
        self._rsi[self._t] = rsi
        return rsi

    @property
    def min_length(self) -> int:
        return self._w


class RsiWilder(BaseIndicator):
    """ Wilder's Relative Strength Index indicator using the EWMA. """

    _NAME = 'rsiwilder'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._alpha = 2. / (1. + w)
        self._c = 1. - self._alpha
        self._rsi = None
        self._up = None
        self._down = None
        self._ma_up = .0
        self._ma_down = .0

        super(RsiWilder, self).__init__(ts, is_bulk)

    def _bulk(self, t0: int) -> None:
        self._rsi = np.empty(self._max_t, dtype=float)
        # self._rsi[:self._w - 1] = np.nan
        self._up = np.empty(self._max_t, dtype=float)
        self._down = np.empty(self._max_t, dtype=float)

        slc = slice(None, None) if self._is_bulk else slice(None, t0 + 1)

        up_d = np.r_[np.nan, np.diff(self._ts[slc])]
        down_d = -np.copy(up_d)
        up_d[up_d < 0.] = 0.
        down_d[down_d < 0.] = 0.

        rs = np.empty(up_d.shape[0], dtype=float)
        rs[0:2] = np.nan

        end = self._max_t if self._is_bulk else t0 + 1
        ma_up = up_d[1]
        ma_down = down_d[1]
        for i in range(2, end):
            ma_up = self._alpha * up_d[i] + self._c * ma_up
            ma_down = self._alpha * down_d[i] + self._c * ma_down
            rs[i] = ma_up / ma_down

        self._up[slc] = up_d
        self._down[slc] = down_d
        self._ma_up = ma_up
        self._ma_down = ma_down
        self._rsi[slc] = 100. - 100. / (1. + rs)

    def get_indicator(self) -> dict:
        return {'rsi': self._rsi}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._rsi[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        up_d = self._ts[self._t] - self._ts[self._t - 1]
        down_d = 0. if up_d > 0. else -up_d
        up_d = 0. if up_d < 0. else up_d

        self._ma_up = self._alpha * up_d + self._c * self._ma_up
        self._ma_down = self._alpha * down_d + self._c * self._ma_down

        rs = self._ma_up / self._ma_down
        rsi = 100. - 100. / (1. + rs)

        self._up[self._t] = up_d
        self._down[self._t] = down_d
        self._rsi[self._t] = rsi
        return rsi

    @property
    def min_length(self) -> int:
        return self._w


class Stochastic(BaseIndicator):
    """ Stochastic Oscillator indicator. """

    _NAME = 'stochastic'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w_price: int,
                 w_k: int, w_d: int):
        if w_k > w_d:
            w_k, w_d = w_d, w_k

        self._wp = w_price
        self._wk = w_k
        self._wd = w_d
        self._p_k = None
        self._p_d = None
        self._p_d_slow = None

        super(Stochastic, self).__init__(ts, is_bulk)

    def _bulk(self, t0: int) -> None:
        # n = self._ts.shape[0]
        # self._ma_pk = np.empty(self._max_t, dtype=float)
        # self._ma_pk[:self._wp - 1] = np.nan
        self._p_k = np.empty(self._max_t, dtype=float)
        self._p_d = np.empty(self._max_t, dtype=float)
        self._p_d_slow = np.empty(self._max_t, dtype=float)

        slc = slice(None, None) if self._is_bulk else slice(None, t0 + 1)

        roll = Math.rolling_window(self._ts[slc], self._wp)
        high = np.r_[
            [np.nan] * (self._wp - 1),
            np.max(roll, axis=1)
        ]
        low = np.r_[
            [np.nan] * (self._wp - 1),
            np.min(roll, axis=1)
        ]

        p_k = (self._ts[slc] - low) / (high - low)
        self._p_k[slc] = p_k
        p_d = np.r_[
            [np.nan] * (self._wk - 1),
            Math.rolling_mean(p_k, self._wk)
        ]

        self._p_d[slc] = p_d
        self._p_d_slow[slc] = np.r_[
            [np.nan] * (self._wd - 1),
            Math.rolling_mean(p_d, self._wd)
        ]

    def get_indicator(self) -> dict:
        return {'p_d': self._p_d, 'p_d_slow': self._p_d_slow}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._p_d[self._t], self._p_d_slow[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        start = self._t - self._wp + 1
        high = np.max(self._ts[start:self._t + 1], axis=0)
        low = np.min(self._ts[start:self._t + 1], axis=0)

        p_k = (self._ts[self._t] - low) / (high - low)
        p_d = self._p_d[self._t - 1] + (p_k - self._p_k[self._t - self._wk]) / self._wk
        p_d_slow = self._p_d_slow[self._t - 1] + (p_d - self._p_d[self._t - self._wd]) / self._wd

        self._p_k[self._t] = p_k
        self._p_d[self._t] = p_d
        self._p_d_slow[self._t] = p_d_slow

        return p_d, p_d_slow

    @property
    def min_length(self) -> int:
        return self._wp + self._wd


class Tr(BaseIndicator):
    """ Calculates the True Range (TR) as the maximum between:
        1. abs(high_{t} - low_{t})
        2. abs(high_{t} - close_{t-1})
        3. abs(low_{t} - close_{t-1})
    The ts array is expected with shape (3, n) with structure:
        <high, low, close>.
    If an array with shape (n,) is provided, the TR is calculated as:
        |ts_{i} - ts_{i-1}|.
    """

    _NAME = 'tr'

    def __init__(self, ts: np.ndarray, is_bulk: bool):
        self._tr = None

        super(Tr, self).__init__(ts, is_bulk)

        if len(ts.shape) == 1:
            self._is_hlc = False
            setattr(self, '_ind', self._ind_c)
        elif (len(ts.shape) == 2) and (ts.shape[0] == 3):
            self._is_hlc = True
            setattr(self, '_ind', self._ind_hlc)
        else:
            raise ValueError(f"Indicator {self._NAME}: Input malformed: ts.shape != (n,) or (3, n)")

    def _bulk(self, t0: int) -> None:
        self._tr = np.empty(self._max_t, dtype=float)
        self._tr[0] = np.nan

        if self._is_hlc:
            if self._is_bulk:
                hl_slc = slice(1, None)
                c_slc = slice(0, -1)
            else:
                hl_slc = slice(1, t0 + 1)
                c_slc = slice(0, t0)
            self._tr[hl_slc] = np.maximum(self._ts[0, hl_slc], self._ts[2, c_slc]) - \
                               np.minimum(self._ts[1, hl_slc], self._ts[2, c_slc])
        else:
            if self._is_bulk:
                hl_slc = slice(1, None)
                c_slc = slice(0, -1)
            else:
                hl_slc = slice(1, t0 + 1)
                c_slc = slice(0, t0)
            self._tr[hl_slc] = np.abs(self._ts[hl_slc] - self._ts[c_slc])

    def get_indicator(self) -> dict:
        return {'tr': self._tr}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._tr[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        pass

    def _ind_c(self) -> float:
        tr = np.abs(self._ts[self._t] - self._ts[self._t - 1])
        self._tr[self._t] = tr
        return tr

    def _ind_hlc(self) -> float:
        prev_close = self._ts[2, self._t - 1]
        tr = max(self._ts[0, self._t], prev_close) - \
             min(self._ts[1, self._t], prev_close)
        self._tr[self._t] = tr
        return tr

    @property
    def min_length(self) -> int:
        return 2


class Tsi(BaseIndicator):
    """ True Strength Index indicator. """

    _NAME = 'tsi'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w_slow: int,
                 w_fast: int):
        self._wf = w_fast
        self._ws = w_slow

        self._af = 2. / (1. + w_fast)
        self._cf = 1. - self._af
        self._as = 2. / (1. + w_slow)
        self._cs = 1. - self._as

        self._tsi = None
        self._ema_fs = None
        self._ema_pc = None
        self._ema_fsabs = None
        self._ema_apc = None

        super(Tsi, self).__init__(ts, is_bulk)

    def _bulk(self, t0: int) -> None:
        self._tsi = np.empty(self._max_t, dtype=float)
        self._ema_fs = np.empty(self._max_t, dtype=float)
        self._ema_pc = np.empty(self._max_t, dtype=float)
        self._ema_fsabs = np.empty(self._max_t, dtype=float)
        self._ema_apc = np.empty(self._max_t, dtype=float)

        def _ewma(out_, v_, a_, c_, start_, end_):
            out_[0] = np.nan
            out_[1] = v_[start_]
            for i in range(start_ + 1, end_):
                out_[i + 1] = a_ * v_[i] + c_ * out_[i]

        end = self._max_t if self._is_bulk else t0 + 1

        d = self._ts[1:end] - self._ts[:end - 1]
        _ewma(self._ema_fs, d, self._as, self._cs, 0, end - 1)
        _ewma(self._ema_pc, self._ema_fs, self._af, self._cf, 1, end)

        d = np.abs(d)
        _ewma(self._ema_fsabs, d, self._as, self._cs, 0, end - 1)
        _ewma(self._ema_apc, self._ema_fsabs, self._af, self._cf, 1, end)

        self._tsi[:end] = 100. * (self._ema_pc[:end] / self._ema_apc[:end])

    def get_indicator(self) -> dict:
        return {'tsi': self._tsi}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._tsi[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        d = self._ts[self._t] - self._ts[self._t - 1]
        fs = self._af * d + self._cf * self._ema_fs[self._t - 1]
        pc = self._as * fs + self._cs * self._ema_pc[self._t - 1]
        self._ema_fs[self._t] = fs
        self._ema_pc[self._t] = pc

        d = np.abs(d)
        fs = self._af * d + self._cf * self._ema_fsabs[self._t - 1]
        apc = self._as * fs + self._cs * self._ema_apc[self._t - 1]
        self._ema_fsabs[self._t] = fs
        self._ema_apc[self._t] = apc

        tsi = 100. * (pc / apc)
        self._tsi[self._t] = tsi
        return tsi

    @property
    def min_length(self) -> int:
        return self._ws + self._wf
