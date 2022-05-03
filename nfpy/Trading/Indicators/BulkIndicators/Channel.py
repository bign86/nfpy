#
# Channel finding
# Functions to individuate trading channels in bulk form.
#

import numpy as np
from typing import Sequence

import nfpy.Math as Math

from .MA import (sma, smstd)
from ..Utils import _check_len


def bollinger(ts: np.ndarray, w: int, alpha: float) -> tuple:
    """ Bollinger Bands indicator.

        Input:
            ts [np.ndarray]: data series
            w [int]: averaging window
            alpha [float]: multiplier of the standard deviation

        Output:
            b_down [np.ndarray]: the Lower Bollinger band
            b_middle [np.ndarray]: the Middle Bollinger band
            b_up [np.ndarray]: the Upper Bollinger band
            b_pct [np.ndarray]: the %b bandwidth band
            b_width [np.ndarray]: the Bandwidth band
    """
    _check_len(ts, w)

    mean = sma(ts, w)
    band_dev = alpha * smstd(ts, w)
    low = mean - band_dev
    high = mean + band_dev
    b_diff = high - low
    bp = (v - low) / b_diff
    b_width = b_diff / mean

    return high, low, mean, bp, b_width


def donchian(ts: np.ndarray, w: int) \
        -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """ Calculates the Donchian Channel indicator.
        The ts array is expected either with shape (n,) if close prices are
        used, or with shape (2, n) with structure:
            <high, low>.

        Input:
            ts [np.ndarray]: price data series
            w [int]: rolling window on price series
    """
    if len(ts.shape) == 1:
        roll = Math.rolling_window(ts, w)
        high = np.nanmax(roll, axis=1)
        low = np.nanmin(roll, axis=1)
    elif len(ts.shape) == 2 and (ts.shape[0] == 2):
        high = np.nanmax(
            Math.rolling_window(ts[0, :], w),
            axis=1
        )
        low = np.nanmin(
            Math.rolling_window(ts[1, :], w),
            axis=1
        )
    else:
        raise ValueError("donchian(): Input malformed: ts.shape != (n,) or (2, n)")

    high = np.r_[[np.nan]*w, high[:-1]]
    low = np.r_[[np.nan]*w, low[:-1]]
    mean = .5 * (high + low)

    return high, low, mean


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
