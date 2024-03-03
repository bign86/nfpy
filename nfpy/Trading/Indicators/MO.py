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

        super(Aroon, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._aro = np.empty(self._max_t, dtype=float)
        self._aro_up = np.empty(self._max_t, dtype=float)
        self._aro_dwn = np.empty(self._max_t, dtype=float)

        self._aro[:self._w - 1] = np.nan
        self._aro_up[:self._w - 1] = np.nan
        self._aro_dwn[:self._w - 1] = np.nan

        # Calculate the Aroon over the relevant time period
        end = None if self._is_bulk else t0 + 1
        ts_slc = slice(None, end)
        a_slc = slice(self._w - 1, end)

        roll = Math.rolling_window(self._ts[ts_slc], self._w)
        up = 100. - 100. * (np.argmax(roll, axis=1) + 1) / self._w
        down = 100. - 100. * (np.argmin(roll, axis=1) + 1) / self._w

        self._aro[a_slc] = up - down
        self._aro_up[a_slc] = up
        self._aro_dwn[a_slc] = down

    def get_indicator(self) -> dict:
        return {'up': self._aro_up, 'down': self._aro_dwn, 'aroon': self._aro}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._aro_up[self._t], self._aro_dwn[self._t], self._aro[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        slc = self._ts[self._t - self._w + 1: self._t + 1]
        up = 100. - 100. * (np.argmax(slc) + 1) / self._w
        down = 100. - 100. * (np.argmin(slc) + 1) / self._w
        aroon = up - down

        self._aro[self._t] = aroon
        self._aro_up[self._t] = up
        self._aro_dwn[self._t] = down
        return up, down, aroon

    @property
    def min_length(self) -> int:
        return self._w


class Adx(BaseIndicator):
    """ Calculates the Average Directional Movement indicator. It a lagging
        trend strength indicator, not a direction or momentum indicator.
        The <ts> array is expected with shape (2, n) and structure
            <high, low, close>.
    """

    _NAME = 'adx'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._alpha = 2. / (1. + w)
        self._c = 1. - self._alpha

        super(Adx, self).__init__(ts, is_bulk, {3})

    def _bulk(self, t0: int) -> None:
        self._dm_up = np.empty(self._max_t, dtype=float)
        self._dm_down = np.empty(self._max_t, dtype=float)
        self._di_up = np.empty(self._max_t, dtype=float)
        self._di_up[0] = np.nan
        self._di_down = np.empty(self._max_t, dtype=float)
        self._di_down[0] = np.nan
        self._tr = np.empty(self._max_t, dtype=float)
        self._tr[0] = np.nan
        self._atr = np.empty(self._max_t, dtype=float)
        self._atr[:self._w] = np.nan
        self._adx = np.empty(self._max_t, dtype=float)
        self._adx[:self._w] = np.nan

        if self._is_bulk:
            m_slc = slice(0, None)
            hl_slc = slice(1, None)
            c_slc = slice(0, -1)
            end = self._max_t
        else:
            m_slc = slice(0, t0 + 1)
            hl_slc = slice(1, t0 + 1)
            c_slc = slice(0, t0)
            end = t0 + 1

        # Calculate ATR
        self._tr[hl_slc] = np.maximum(self._ts[0, hl_slc], self._ts[2, c_slc]) - \
                           np.minimum(self._ts[1, hl_slc], self._ts[2, c_slc])

        atr = np.mean(self._tr[1:self._w + 1])
        self._atr[self._w] = atr

        for i in range(self._w + 1, end):
            # https://en.wikipedia.org/wiki/Average_true_range
            atr = (atr * (self._w - 1) + self._tr[i]) / self._w
            self._atr[i] = atr

        # Calculate the Directional indicator
        upmove = np.diff(self._ts[0, m_slc])
        downmove = np.diff(self._ts[1, m_slc][::-1])[::-1]

        mask = (upmove > downmove) & (upmove > 0)
        upmove[~mask] = .0
        mask = (downmove > upmove) & (downmove > 0)
        downmove[~mask] = .0

        self._dm_up[m_slc] = np.r_[np.nan, upmove]
        self._dm_down[m_slc] = np.r_[np.nan, downmove]

        # Calculate the smoothed DI
        self._di_up[1] = self._dm_up[1]
        self._di_down[1] = self._dm_down[1]
        for i in range(2, end):
            self._di_up[i] = self._alpha * self._dm_up[i] + self._c * self._di_up[i - 1]
            self._di_down[i] = self._alpha * self._dm_down[i] + self._c * self._di_down[i - 1]

        # Divide the DI by the ATR
        norm_di_up = self._di_up[m_slc] / self._atr[m_slc]
        norm_di_down = self._di_down[m_slc] / self._atr[m_slc]

        raw_adx = (np.abs(norm_di_up - norm_di_down) / (norm_di_up + norm_di_down))
        self._adx[self._w] = raw_adx[self._w]
        for i in range(self._w + 1, end):
            self._adx[i] = self._alpha * raw_adx[i] + self._c * self._adx[i - 1]

    def get_indicator(self) -> dict:
        return {
            'adx': self._adx,
            'dm+': self._dm_up, 'dm-': self._dm_down,
            'di+': self._di_up, 'di-': self._di_down,
            'tr': self._tr, 'atr': self._atr,
        }

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._adx[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        # Calculate ATR
        prev_close = self._ts[2, self._t - 1]
        tr = max(self._ts[0, self._t], prev_close) - \
             min(self._ts[1, self._t], prev_close)
        atr = (self._atr[self._t - 1] * (self._w - 1) + tr) / self._w

        # Calculate the Directional indicator
        upmove = self._ts[0, self._t] - self._ts[0, self._t - 1]
        downmove = self._ts[1, self._t - 1] - self._ts[1, self._t]

        if not ((upmove > downmove) & (upmove > 0)):
            upmove = .0
        if not ((downmove > upmove) & (downmove > 0)):
            downmove = .0

        # Calculate the smoothed DI
        di_up = self._alpha * upmove + self._c * self._di_up[self._t - 1]
        di_down = self._alpha * downmove + self._c * self._di_down[self._t - 1]

        # Divide the DI by the ATR
        norm_di_up = di_up / atr
        norm_di_down = di_down / atr

        raw_adx = (np.abs(norm_di_up - norm_di_down) / (norm_di_up + norm_di_down))
        adx = self._alpha * raw_adx + self._c * self._adx[self._t - 1]

        self._dm_up[self._t] = upmove
        self._dm_down[self._t] = downmove
        self._di_up[self._t] = di_up
        self._di_down[self._t] = di_down
        self._tr[self._t] = tr
        self._atr[self._t] = atr
        self._adx[self._t] = adx
        return adx

    @property
    def min_length(self) -> int:
        return self._w + 1


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
        self._tr = None
        self._atr = None

        super(Atr, self).__init__(ts, is_bulk, {1, 3})

        if (ts.ndim == 2) and (ts.shape[0] == 3):
            self._is_hlc = True
            if not self._is_bulk:
                setattr(self, '_ind', self._ind_hlc)
        elif (ts.ndim == 2) and (ts.shape[0] == 1):
            self._ts = np.flatten(self._ts)
        else:
            self._is_hlc = False
            if not self._is_bulk:
                setattr(self, '_ind', self._ind_c)

    def _bulk(self, t0: int) -> None:
        self._atr = np.empty(self._max_t, dtype=float)
        self._tr = np.empty(self._max_t, dtype=float)
        self._atr[:self._w] = np.nan
        self._tr[0] = np.nan

        # Calculate the TR over the relevant time period
        if self._is_bulk:
            hl_slc = slice(1, None)
            c_slc = slice(0, -1)
        else:
            hl_slc = slice(1, t0 + 1)
            c_slc = slice(0, t0)

        if self._is_hlc:
            self._tr[hl_slc] = np.maximum(self._ts[0, hl_slc], self._ts[2, c_slc]) - \
                               np.minimum(self._ts[1, hl_slc], self._ts[2, c_slc])
        else:
            self._tr[hl_slc] = np.abs(self._ts[hl_slc] - self._ts[c_slc])

        # Calculate the first point for the ATR using a simple average
        atr = np.mean(self._tr[1:self._w + 1])
        self._atr[self._w] = atr

        end = self._max_t if self._is_bulk else t0 + 1
        for i in range(self._w + 1, end):
            # Calculate the remaining points as an exponential average
            # https://en.wikipedia.org/wiki/Average_true_range
            atr = (atr * (self._w - 1) + self._tr[i]) / self._w
            self._atr[i] = atr

    def get_indicator(self) -> dict:
        return {'atr': self._atr}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._atr[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        pass

    def _ind_c(self) -> float:
        tr = np.abs(self._ts[self._t] - self._ts[self._t - 1])
        self._tr[self._t] = tr

        atr = (self._atr[self._t - 1] * (self._w - 1) + tr) / self._w
        self._atr[self._t] = atr
        return atr

    def _ind_hlc(self) -> float:
        prev_close = self._ts[2, self._t - 1]
        tr = max(self._ts[0, self._t], prev_close) - \
             min(self._ts[1, self._t], prev_close)
        self._tr[self._t] = tr

        atr = (self._atr[self._t - 1] * (self._w - 1) + tr) / self._w
        self._atr[self._t] = atr
        return atr

    @property
    def min_length(self) -> int:
        return max(2, self._w + 1)


class Cci(BaseIndicator):
    """ Calculates the Commodity Channel Index indicator. The <ts> array
        is expected to have shape (n, ) or shape (3, n) with each row having
        the structure:
            <high, low, close>.
    """

    _NAME = 'cci'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._cci = None
        self._dmean = None
        self._sma = .0
        self._mad = .0

        super(Cci, self).__init__(ts, is_bulk, {1, 3})

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
        self._cci = np.empty(self._max_t, dtype=float)
        self._cci[:self._w - 1] = np.nan
        self._dmean = np.empty(self._max_t, dtype=float)

        end = None if self._is_bulk else t0 + 1
        ma_slc = slice(None, end)
        cci_slc = slice(self._w - 1, end)

        if self._is_hlc:
            p = np.sum(self._ts[:, ma_slc], axis=0) / 3.
        else:
            p = self._ts[ma_slc]

        sma = Math.rolling_mean(p, self._w)
        sma = np.r_[[sma[0]] * (self._w - 1), sma]
        self._dmean[ma_slc] = p - sma
        mad = Math.rolling_mean(np.abs(self._dmean[ma_slc]), self._w)
        self._sma = float(sma[-1])
        self._mad = float(mad[-1])

        self._cci[cci_slc] = self._dmean[cci_slc] / (.015 * mad)

    def get_indicator(self) -> dict:
        return {'cci': self._cci}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._cci[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        pass

    def _ind_c(self) -> float:
        self._sma += (self._ts[self._t] - self._ts[self._t - self._w]) / self._w
        dmean = self._ts[self._t] - self._sma
        self._dmean[self._t] = dmean
        self._mad += (np.abs(dmean) - np.abs(self._dmean[self._t - self._w])) / self._w
        cci = dmean / (.015 * self._mad)
        self._cci[self._t] = cci
        return cci

    def _ind_hlc(self) -> float:
        p = np.sum(self._ts[:, self._t]) / 3.
        p_old = np.sum(self._ts[:, self._t - self._w]) / 3.
        self._sma += (p - p_old) / self._w
        dmean = p - self._sma
        self._dmean[self._t] = dmean
        self._mad += (np.abs(dmean) - np.abs(self._dmean[self._t - self._w])) / self._w
        cci = dmean / (.015 * self._mad)
        self._cci[self._t] = cci
        return cci

    @property
    def min_length(self) -> int:
        return self._w


class Dmi(BaseIndicator):
    """ Calculates the Directional Movement Index indicator.
        The <ts> array is expected with shape (2, n) and structure
            <high, low, close>.
    """

    _NAME = 'dmi'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._alpha = 2. / (1. + w)
        self._c = 1. - self._alpha

        super(Dmi, self).__init__(ts, is_bulk, {3})

    def _bulk(self, t0: int) -> None:
        self._dm_up = np.empty(self._max_t, dtype=float)
        self._dm_down = np.empty(self._max_t, dtype=float)
        self._di_up = np.empty(self._max_t, dtype=float)
        self._di_up[0] = np.nan
        self._di_down = np.empty(self._max_t, dtype=float)
        self._di_down[0] = np.nan

        m_slc = slice(0, None) if self._is_bulk else slice(0, t0 + 1)

        # Calculate the Directional indicator
        upmove = np.diff(self._ts[0, m_slc])
        downmove = np.diff(self._ts[1, m_slc][::-1])[::-1]

        mask = (upmove > downmove) & (upmove > 0)
        upmove[~mask] = .0
        mask = (downmove > upmove) & (downmove > 0)
        downmove[~mask] = .0

        self._dm_up[m_slc] = np.r_[np.nan, upmove]
        self._dm_down[m_slc] = np.r_[np.nan, downmove]

        # Calculate the smoothed DI
        end = self._max_t if self._is_bulk else t0 + 1

        self._di_up[1] = self._dm_up[1]
        self._di_down[1] = self._dm_down[1]
        for i in range(2, end):
            self._di_up[i] = self._alpha * self._dm_up[i] + self._c * self._di_up[i - 1]
            self._di_down[i] = self._alpha * self._dm_down[i] + self._c * self._di_down[i - 1]

    def get_indicator(self) -> dict:
        return {
            'dm+': self._dm_up, 'dm-': self._dm_down,
            'di+': self._di_up, 'di-': self._di_down,
        }

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._di_up[self._t], self._di_down[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        # Calculate the Directional indicator
        upmove = self._ts[0, self._t] - self._ts[0, self._t - 1]
        downmove = self._ts[1, self._t - 1] - self._ts[1, self._t]

        if not ((upmove > downmove) & (upmove > 0)):
            upmove = .0
        if not ((downmove > upmove) & (downmove > 0)):
            downmove = .0

        # Calculate the smoothed DI
        di_up = self._alpha * upmove + self._c * self._di_up[self._t - 1]
        di_down = self._alpha * downmove + self._c * self._di_down[self._t - 1]

        self._dm_up[self._t] = upmove
        self._dm_down[self._t] = downmove
        self._di_up[self._t] = di_up
        self._di_down[self._t] = di_down
        return di_up, di_down

    @property
    def min_length(self) -> int:
        return max(2, self._w)


class Fi(BaseIndicator):
    """ Force Index indicator calculation. It is the price difference scaled by
        the trade volume. The input must have shape (2, n) and be like:
            <price, volume>.
    """

    _NAME = 'fi'

    def __init__(self, ts: np.ndarray, is_bulk: bool):
        self._fi = None

        super(Fi, self).__init__(ts, is_bulk, {2})

    def _bulk(self, t0: int) -> None:
        self._fi = np.empty(self._max_t, dtype=float)

        end = None if self._is_bulk else t0 + 1
        df_slc = slice(None, end)
        ts_slc = slice(1, end)

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
        13-periods is common.
    """

    _NAME = 'fielder'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._fi = None
        self._fie = None

        super(FiElder, self).__init__(ts, is_bulk, {2})

    def _bulk(self, t0: int) -> None:
        self._fi = np.empty(self._max_t, dtype=float)
        self._fie = np.empty(self._max_t, dtype=float)
        self._fie[:self._w - 1] = np.nan

        end = None if self._is_bulk else t0 + 1
        df_slc = slice(None, end)
        ts_slc = slice(1, end)
        out_slc = slice(self._w - 1, end)

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
        return self._w + 1


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

        if ts.shape[0] == 4:
            tp = np.sum(ts[:3, :], axis=1) / 3.
            ts = np.vstack(tp, ts[3, :])

        super(Mfi, self).__init__(ts, is_bulk, {2})

    def _bulk(self, t0: int) -> None:
        self._mfi = np.empty(self._max_t, dtype=float)
        self._mfi[:self._w - 1] = np.nan
        self._pos_mf = np.empty(self._max_t, dtype=int)
        self._neg_mf = np.empty(self._max_t, dtype=int)

        end = None if self._is_bulk else t0 + 1
        ts_slc = slice(None, end)
        mfi_slc = slice(self._w - 1, end)

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
        self._pos_mf[self._t] = 1 if raw_money_flow >= .0 else 0
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


# FIXME: check again
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

        super(RsiCutler, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._rsi = np.empty(self._max_t, dtype=float)
        self._rsi[:self._w - 1] = np.nan
        self._up = np.empty(self._max_t, dtype=float)
        self._down = np.empty(self._max_t, dtype=float)

        end = None if self._is_bulk else t0 + 1
        slc = slice(None, end)
        rsi_slc = slice(self._w - 1, end)

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
        return self._w + 1


# FIXME: check again
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

        super(RsiWilder, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._rsi = np.empty(self._max_t, dtype=float)
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
    """ Stochastic Oscillator indicator. Typical values are <5, 3, 3>. """

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

        super(Stochastic, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
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
        return self._wp + self._wd - 1


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

        super(Tr, self).__init__(ts, is_bulk, {1, 3})

        if len(ts.shape) == 1:
            self._is_hlc = False
            setattr(self, '_ind', self._ind_c)
        elif len(ts.shape) == 2:
            self._is_hlc = True
            setattr(self, '_ind', self._ind_hlc)
        else:
            raise ValueError(f"Indicator {self._NAME}: Input malformed: ts.shape != (n,) or (3, n)")

    def _bulk(self, t0: int) -> None:
        self._tr = np.empty(self._max_t, dtype=float)
        self._tr[0] = np.nan

        if self._is_bulk:
            hl_slc = slice(1, None)
            c_slc = slice(0, -1)
        else:
            hl_slc = slice(1, t0 + 1)
            c_slc = slice(0, t0)

        if self._is_hlc:
            self._tr[hl_slc] = np.maximum(self._ts[0, hl_slc], self._ts[2, c_slc]) - \
                               np.minimum(self._ts[1, hl_slc], self._ts[2, c_slc])
        else:
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
        return 1


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
        self._ema_pcabs = None

        super(Tsi, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        self._tsi = np.empty(self._max_t, dtype=float)
        self._ema_fs = np.empty(self._max_t, dtype=float)
        self._ema_pc = np.empty(self._max_t, dtype=float)
        self._ema_fsabs = np.empty(self._max_t, dtype=float)
        self._ema_pcabs = np.empty(self._max_t, dtype=float)

        def _ewma(out_, m_, a_, start_, end_):
            out_[:start_ + 1] = m_[:start_ + 1]
            for i in range(start_ + 1, end_):
                out_[i] = a_ * (m_[i] - out_[i - 1]) + out_[i - 1]

        end = self._max_t if self._is_bulk else t0 + 1

        mom = np.r_[.0, self._ts[1:end] - self._ts[:end - 1]]
        _ewma(self._ema_fs, mom, self._as, 0, end)
        _ewma(self._ema_pc, self._ema_fs, self._af, 1, end)

        mom = np.abs(mom)
        _ewma(self._ema_fsabs, mom, self._as, 0, end)
        _ewma(self._ema_pcabs, self._ema_fsabs, self._af, 1, end)

        self._tsi[:end] = 100. * (self._ema_pc[:end] / self._ema_pcabs[:end])

    def get_indicator(self) -> dict:
        return {'tsi': self._tsi}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._tsi[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        mom = self._ts[self._t] - self._ts[self._t - 1]
        fs = self._as * (mom - self._ema_fs[self._t - 1]) + self._ema_fs[self._t - 1]
        pc = self._af * (fs - self._ema_pc[self._t - 1]) + self._ema_pc[self._t - 1]
        self._ema_fs[self._t] = fs
        self._ema_pc[self._t] = pc

        mom = np.abs(mom)
        fs = self._as * (mom - self._ema_fsabs[self._t - 1]) + self._ema_fsabs[self._t - 1]
        apc = self._af * (fs - self._ema_pcabs[self._t - 1]) + self._ema_pcabs[self._t - 1]
        self._ema_fsabs[self._t] = fs
        self._ema_pcabs[self._t] = apc

        tsi = 100. * (pc / apc)
        self._tsi[self._t] = tsi
        return tsi

    @property
    def min_length(self) -> int:
        return self._ws + self._wf - 1


class Vwap(BaseIndicator):
    """ Calculates the Volume Weighted Average Price (VWAP). The ts array is
        expected with shape (2, n) with structure:
            <close, volume>.
    """

    _NAME = 'vwap'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int):
        self._w = w
        self._vwap = None

        super(Vwap, self).__init__(ts, is_bulk, {2})

    def _bulk(self, t0: int) -> None:
        self._vwap = np.empty(self._max_t, dtype=float)

        end = self._max_t if self._is_bulk else t0 + 1
        p = Math.rolling_window(self._ts[0, :end], self._w)
        v = Math.rolling_window(self._ts[1, :end], self._w)

        self._vwap[:end] = np.r_[
            [np.nan] * (self._w - 1),
            np.nansum(p * v, axis=1) / np.nansum(v, axis=1)
        ]

    def get_indicator(self) -> dict:
        return {'vwap': self._vwap}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._vwap[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        t_last = self._t + 1
        t_old = t_last - self._w
        p = self._ts[0, t_old:t_last]
        v = self._ts[1, t_old:t_last]
        vwap = np.nansum(p * v) / np.nansum(v)
        self._vwap[self._t] = vwap
        return vwap

    @property
    def min_length(self) -> int:
        return self._w
