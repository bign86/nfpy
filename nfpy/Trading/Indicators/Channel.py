#
# Channel finding
# Functions to individuate trading channels in bulk form.
#

import numpy as np
from typing import (Sequence, Union)

import nfpy.Math as Math

from .BaseIndicator import BaseIndicator


class Bollinger(BaseIndicator):
    """ Bollinger Bands indicator. """

    _NAME = 'bollinger'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int, alpha: float):
        self._w = w
        self._alpha = alpha

        self._ma = None
        self._low = None
        self._high = None
        self._bp = None
        self._b_width = None

        super(Bollinger, self).__init__(ts, is_bulk, {1})

    def _bulk(self, t0: int) -> None:
        n = self._ts.shape[0]
        self._ma = np.empty(n, dtype=float)
        self._low = np.empty(n, dtype=float)
        self._high = np.empty(n, dtype=float)
        self._bp = np.empty(n, dtype=float)
        self._b_width = np.empty(n, dtype=float)

        ts_slc = slice(None, None) if self._is_bulk else slice(None, t0 + 1)

        ts = self._ts[ts_slc]
        ts2d = Math.rolling_window(ts, self._w)
        mean = np.r_[[np.nan] * (self._w - 1), np.mean(ts2d, axis=1)]
        band_dev = np.r_[
            [np.nan] * (self._w - 1),
            self._alpha * np.std(ts2d, axis=1, ddof=1)
        ]

        low = mean - band_dev
        high = mean + band_dev
        b_diff = 2. * band_dev
        self._bp[ts_slc] = (ts - low) / b_diff
        self._b_width[ts_slc] = b_diff / mean
        self._low[ts_slc] = low
        self._high[ts_slc] = high
        self._ma[ts_slc] = mean

    def get_indicator(self) -> dict:
        return {'high': self._high, 'mean': self._ma, 'low': self._low,
                '%b': self._bp, 'width': self._b_width}

    def _ind_bulk(self) -> Union[float, tuple]:
        return (self._high[self._t], self._ma[self._t], self._low[self._t],
                self._bp[self._t], self._b_width[self._t])

    def _ind_online(self) -> Union[float, tuple]:
        ts = self._ts
        ma = self._ma[self._t - 1] + (ts[self._t] - ts[self._t - self._w]) / self._w
        std = self._alpha * np.std(ts[self._t - self._w + 1:self._t + 1], axis=0, ddof=1)
        low = ma - std
        high = ma + std
        b_diff = 2. * std
        bp = (ts[self._t] - low) / b_diff
        b_width = b_diff / ma

        self._bp[self._t] = bp
        self._b_width[self._t] = b_width
        self._low[self._t] = low
        self._high[self._t] = high
        self._ma[self._t] = ma
        return high, ma, low, bp, b_width

    @property
    def min_length(self) -> int:
        return self._w


class Donchian(BaseIndicator):
    """ Donchian Channels indicator. The indicator is based on a <w> sliding
        window. The <shift> parameters moves the channel forward by the given
        number of periods.
        The ts array is expected either with shape (n,) if close prices are
        used, or with shape (2, n) with structure:
            <high, low>.
    """

    _NAME = 'donchian'

    def __init__(self, ts: np.ndarray, is_bulk: bool, w: int, shift: int):
        self._w = w
        self._shift = abs(shift)
        self._ma = None
        self._low = None
        self._high = None

        super(Donchian, self).__init__(ts, is_bulk, {1, 2})

        if ts.ndim == 1:
            self._is_hl = False
            if not self._is_bulk:
                setattr(self, '_ind', self._ind_c)
        else:
            self._is_hl = True
            if not self._is_bulk:
                setattr(self, '_ind', self._ind_hl)

    def _bulk(self, t0: int) -> None:
        n = self._ts.shape[0]
        self._ma = np.empty(n, dtype=float)
        self._low = np.empty(n, dtype=float)
        self._high = np.empty(n, dtype=float)

        wasted = self._w + self._shift - 1
        self._ma[:wasted] = np.nan
        self._low[:wasted] = np.nan
        self._high[:wasted] = np.nan

        ts_slc = slice(None, n - self._shift) if self._is_bulk \
            else slice(None, t0 - self._shift + 1)

        if self._is_hl:
            high = np.r_[
                [np.nan] * wasted,
                np.max(
                    Math.rolling_window(self._ts[0, ts_slc], self._w),
                    axis=1
                )]
            low = np.r_[
                [np.nan] * wasted,
                np.min(
                    Math.rolling_window(self._ts[1, ts_slc], self._w),
                    axis=1
                )]
        else:
            roll = Math.rolling_window(self._ts[ts_slc], self._w)
            high = np.max(roll, axis=1)
            low = np.min(roll, axis=1)

        rw_slc = slice(wasted, None) \
            if self._is_bulk else slice(wasted, t0 + 1)
        self._low[rw_slc] = low
        self._high[rw_slc] = high
        self._ma[rw_slc] = .5 * (high + low)

    def get_indicator(self) -> dict:
        return {'high': self._high, 'mean': self._ma, 'low': self._low}

    def _ind_bulk(self) -> Union[float, tuple]:
        return self._high[self._t], self._ma[self._t], self._low[self._t]

    def _ind_online(self) -> Union[float, tuple]:
        pass

    def _ind_c(self) -> Union[float, tuple]:
        ts = self._ts[self._t - self._w - self._shift + 1:self._t - self._shift + 1]
        high = np.max(ts)
        low = np.min(ts)
        mean = .5 * (high + low)

        self._ma[self._t] = mean
        self._high[self._t] = high
        self._low[self._t] = low
        return high, mean, low

    def _ind_hl(self) -> Union[float, tuple]:
        ts = self._ts[:, self._t - self._w - self._shift + 1:self._t - self._shift + 1]
        high = np.max(ts[0, :])
        low = np.min(ts[1, :])
        mean = .5 * (high + low)

        self._ma[self._t] = mean
        self._high[self._t] = high
        self._low[self._t] = low
        return high, mean, low

    @property
    def min_length(self) -> int:
        return self._w + self._shift


def _find_raw_channel(v: np.ndarray, w: int) -> tuple:
    idx_w = list(range(0, v.shape[0], w))
    max_min_idx = np.empty((2, len(idx_w)), dtype=int)

    idx_w.append(v.shape[0])
    for i, n in enumerate(idx_w[:-1]):
        end = idx_w[i + 1]
        max_min_idx[0, i] = np.nanargmax(v[n:end]) + n
        max_min_idx[1, i] = np.nanargmin(v[n:end]) + n

    reg_max = np.polyfit(max_min_idx[0, :], v[max_min_idx[0, :]], 1)
    reg_min = np.polyfit(max_min_idx[1, :], v[max_min_idx[1, :]], 1)

    return reg_max, reg_min, max_min_idx


def search_channel(v: np.ndarray, ws: int, wl: Sequence):
    length = v.shape[0]
    num_wl = len(wl)

    if max(wl) > length:
        msg = f'Window too large: {length} window | {max(wl)} series'
        raise ValueError(msg)
    elif ws > 2 * min(wl):
        msg = f'Subdivision too large: {ws} subdivision | {min(wl)} window'
        raise ValueError(msg)

    chls = np.empty((num_wl, 2, 2), dtype=float)
    indexes = []
    for i, w_size in enumerate(wl):
        rmax, rmin, idx = _find_raw_channel(v[-w_size:], ws)
        chls[i, 0, :] = rmax
        chls[i, 1, :] = rmin
        indexes.append(idx)

    # Search for best window looking at parallelism and distance between lines
    # Score gets higher the most un-parallel are the two regressions
    slope_diff = np.abs(np.diff(chls[:, :, 0], axis=1)).ravel()
    slope_diff /= np.sum(slope_diff)

    # Score get higher the more distance the two lines are. The length of the
    # window is taken into account.
    wl = np.tile(np.array(wl).reshape(num_wl, 1), 2)
    incpt_dist_start = np.diff(chls[:, :, 1], axis=1)
    incpt_dist_end = np.diff(chls[:, :, 1] + wl * chls[:, :, 0], axis=1)
    incpt_num = .5 * (incpt_dist_start + incpt_dist_end).ravel() / chls[:, 1, 1]
    incpt_dist = np.abs(incpt_num / np.sqrt(wl[:, 0]))
    incpt_dist /= np.sum(incpt_dist)

    # print('np.sqrt(wl[:, 0])', np.sqrt(wl[:, 0]))
    # print('slope_diff', slope_diff)
    # print('incpt_dist', incpt_dist)
    # print('total', slope_diff + incpt_dist)

    # The lowest overall score gives the best result
    opt_idx = int(np.argmin(slope_diff + incpt_dist))
    opt_reg = chls[opt_idx, :, :]
    opt_maxmin_idx = indexes[opt_idx]
    opt_wl = wl[opt_idx, 0]

    # Adjust intercept
    real_pos_max = opt_maxmin_idx[0, :] + length - opt_wl
    real_pos_min = opt_maxmin_idx[1, :] + length - opt_wl

    # print(f'===> {wl[opt_idx, 0]}')
    #
    # import matplotlib.pyplot as plt
    # plt.plot(v, color='b')
    # plt.plot((length - opt_wl, length), (opt_reg[0, 1], opt_reg[0, 0] * opt_wl + opt_reg[0, 1]), color='g')
    # plt.plot((length - opt_wl, length), (opt_reg[1, 1], opt_reg[1, 0] * opt_wl + opt_reg[1, 1]), color='r')
    # plt.show()

    opt_reg[0, 1] = np.nanmax(v[real_pos_max] - opt_reg[0, 0] * opt_maxmin_idx[0, :])
    opt_reg[1, 1] = np.nanmin(v[real_pos_min] - opt_reg[1, 0] * opt_maxmin_idx[1, :])

    # plt.plot(v, color='b')
    # plt.plot((length - opt_wl, length), (opt_reg[0, 1], opt_reg[0, 0] * opt_wl + opt_reg[0, 1]), color='g')
    # plt.plot((length - opt_wl, length), (opt_reg[1, 1], opt_reg[1, 0] * opt_wl + opt_reg[1, 1]), color='r')
    # plt.show()

    return opt_reg
