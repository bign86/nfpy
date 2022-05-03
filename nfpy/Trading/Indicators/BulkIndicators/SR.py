#
# S/R finding
# Algorithms to find Support/Resistance levels in a bulk form.
#

import numpy as np
from typing import Sequence

import nfpy.Math as Math


def _get_initial_trend(p: np.ndarray, thrs: float) -> int:
    r = p[1:] / p[0] - 1.
    mask = (r > thrs) | (r < -thrs)

    i = 0
    max_len = r.shape[0]
    try:
        while not mask[i]:
            i += 1
            if i == max_len:
                raise StopIteration
    except StopIteration:
        trend = 0
    else:
        trend = -1 if r[i] < .0 else 1

    return trend


def _search_centroids(dt: np.ndarray, ts: np.ndarray, flags: np.ndarray,
                      tol: float) -> tuple:
    """ S/R centroid search. """
    extrema = ts[flags]

    sort_idx = np.argsort(extrema)
    sort_ext = extrema[sort_idx]
    diff = np.diff(sort_ext)

    ret = ts[1:] / ts[:-1] - 1.
    ret[ret == np.inf] = .0
    sigma = float(np.nanstd(ret))

    mask_grp = np.empty_like(sort_ext, dtype=np.bool)
    mask_grp[0] = True
    mask_grp[1:] = diff > sort_ext[1:] * sigma * tol
    groups = np.cumsum(mask_grp)

    i = np.max(groups)
    centroids = np.empty(i)
    for n in range(i):
        centroids[n] = np.mean(sort_ext[groups == n + 1])

    unsort = np.argsort(sort_idx[mask_grp])
    dates = dt[flags][sort_idx][mask_grp][unsort]

    return centroids[unsort], dates


def _search_pivots(p: np.ndarray, thrs: float) -> np.ndarray:
    """ S/R search using the pivot levels algorithm. """
    up_thrs = 1. + thrs
    down_thrs = 1. - thrs

    flags = np.zeros(p.shape, dtype=int)
    start_idx = Math.next_valid_index(p)

    trend = _get_initial_trend(p[start_idx:], thrs)
    pivot_idx = 0
    last_found = 0

    for i in range(start_idx + 1, p.shape[0]):
        r = p[i] / p[pivot_idx]

        if trend == 1:
            if r > up_thrs:
                flags[pivot_idx] = -1
                last_found = pivot_idx
                trend = -1
                pivot_idx = i
            elif r < 1.:
                pivot_idx = i
        else:
            if r < down_thrs:
                flags[pivot_idx] = 1
                last_found = pivot_idx
                trend = 1
                pivot_idx = i
            elif r > 1.:
                pivot_idx = i

    last_idx = Math.last_valid_index(p)
    flags[last_idx] = 1 if p[last_idx] > p[last_found] else -1

    return flags


def _search_smooth(ts: np.ndarray, w: int) -> np.ndarray:
    """ S/R search using the smoothed signal algorithm. """
    # v = Math.ffill_cols(ts)
    idx, flags = Math.find_relative_extrema(
        Math.smooth(ts, w=w),
        max(w // 10, 1)
    )

    # Clean from consecutive indexes, considered false positives
    ext_distance = np.diff(idx)
    fp = np.where(ext_distance == 1)[0]
    to_del = np.concatenate((fp, fp + 1))
    if to_del:
        idx = np.delete(idx, to_del)
        flags = np.delete(flags, to_del)

    # Divide maxima and minima
    i_max = idx[flags]
    i_min = idx[~flags]

    # Find real price maxima/minima
    w_2 = w // 4  # This is somewhat arbitrary, let's see whether it works
    stride = Math.rolling_window(ts, 2 * w_2 + 1)

    i_max = np.minimum(i_max - w_2, stride.shape[0] - 1)
    maxima = np.nanargmax(stride[i_max, :], axis=1) + i_max

    i_min = np.minimum(i_min - w_2, stride.shape[0] - 1)
    minima = np.nanargmin(stride[i_min, :], axis=1) + i_min

    flags = np.zeros(ts.shape, dtype=int)
    flags[maxima] = 1
    flags[minima] = -1

    return flags


def merge_sr(groups: Sequence[np.ndarray], vola: float) -> Sequence[np.ndarray]:
    """ Remove redundant S/R lines from S/R groups. The groups must be supplied
        in order of priority. The first group is retained intact, the S/R lines
        in following groups are compared to the ones in previous groups. If a
        line falls in the confidence band of another S/R line generated using
        the daily return volatility, the line is deleted.

        Input:
            vola [float]: returns volatility
            groups [Sequence[np.ndarray]]: sequence of S/R groups in order of
                priority

        Output:
            res [list[np.ndarray]]: S/R groups amended
    """
    if len(groups) == 1:
        return groups

    result = [groups[0]]

    v = np.concatenate(groups[:-1])
    v = np.tile(v, (2, 1))
    v[0, :] *= (1. + vola)
    v[1, :] *= (1. - vola)

    count = groups[0].shape[0]
    for g in groups[1:]:
        to_add = []
        for i in g:
            all_in = np.any((i < v[0, :count]) & (i > v[1, :count]))
            if not all_in:
                to_add.append(i)
        result.append(np.array(to_add))
        count += len(g)

    return result


def sr_pivot(dt: np.ndarray, ts: np.ndarray, thrs: float, tol: float = 1.) \
        -> tuple:
    """ Search Support/Resistance lines using the maxima/minima found as pivotal
        levels of the price signal given a return threshold.

        Input:
            dt [np.ndarray]: input dates series
            ts [np.ndarray]: input values series
            thrs [float]: return threshold
            tol [float]: multiplication factor to the volatility for grouping

        Output:
            centers [np.ndarray]: array of S/R lines
            dates [np.ndarray]: array of S/R start dates
    """
    return _search_centroids(
        dt, ts,
        _search_pivots(ts, thrs),
        tol
    )


def sr_smooth(dt: np.ndarray, ts: np.ndarray, w: int, tol: float = 1.) \
        -> tuple:
    """ Search Support/Resistance lines using the maxima/minima of the smoothed
        price curve given a rolling window.

        Input:
            dt [np.ndarray]: input dates series
            ts [np.ndarray]: input values series
            w [int]: list of locations to verify
            tol [float]: multiplication factor to the volatility for grouping

        Output:
            centers [np.ndarray]: array of S/R lines
            dates [np.ndarray]: array of S/R start dates
    """
    return _search_centroids(
        dt, ts,
        _search_smooth(ts, w),
        tol
    )
