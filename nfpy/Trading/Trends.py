#
# Trends functions
# Functions to trends in time series such as extrema (maxima and minima),
# support/resistance lines, trendlines, wedges.
#

import numpy as np
from typing import Sequence

import nfpy.Financial.Math as Math


def _smooth(ts: np.ndarray, w: int) -> np.ndarray:
    """ Smooth a time series.

        Input:
            ts [np.ndarray]: time series to smooth
            w [int]: smoothing window

        Output:
            smooth [np.ndarray]: smoothed time series
    """
    x = Math.ffill_cols(ts)

    if w < 2:
        return x
    elif x.shape[0] < w:
        raise ValueError("Input vector needs to be bigger than window size.")

    if w % 2 == 0:
        w = w + 1
    h = w // 2

    s = np.r_[x[w - 1:0:-1], x, x[-2:-w - 1:-1]]
    wgt = np.hamming(w)

    c = np.convolve(wgt / wgt.sum(), s, mode='valid')
    return c[h:-h]


def _find_minima(dt: np.ndarray, v: np.ndarray) -> tuple:
    """ Find the minima of a series.

        Input:
            dt [np.ndarray]: Input dates series
            v [np.ndarray]: Input values series

        Output:
            dt_res [np.ndarray]: output dates series of maxima
            v_res [np.ndarray]: output values series of maxima
            idx [list]: list of numeric indices found
    """
    dt_res, v_res = dt[1:-1], v[1:-1]
    v_diff = ((v_res - v[:-2]) < .0) & ((v_res - v[2:]) < .0)
    dt_res, v_res = dt_res[v_diff], v_res[v_diff]
    idx = np.where(v_diff)[0] + 1
    return dt_res, v_res, idx


# def is_minima(ts: pd.Series, idx_list: Sequence) -> Sequence:
#     """ Check whether a sequence of indices corresponds to minima.
#
#         Input:
#             ts [pd.Series]: Input series
#             idx_list [Sequence]: list of locations to verify
#
#         Output:
#             res [Sequence]: output series of truth values
#     """
#     ts_diff = [False] * len(idx_list)
#     for i, idx in enumerate(idx_list):
#         loc = ts.index.get_loc(idx)
#         try:
#             if (ts.iat[loc] < ts.iat[loc - 1]) & (ts.iat[loc] < ts.iat[loc + 1]):
#                 ts_diff[i] = True
#         except IndexError:
#             pass
#     return ts_diff


def _find_maxima(dt: np.ndarray, v: np.ndarray) -> tuple:
    """ Find the maxima of a series.

        Input:
            dt [np.ndarray]: Input dates series
            v [np.ndarray]: Input values series

        Output:
            dt_res [np.ndarray]: output dates series of maxima
            v_res [np.ndarray]: output values series of maxima
            idx [list]: list of numeric indices found
    """
    dt_res, v_res = dt[1:-1], v[1:-1]
    v_diff = ((v_res - v[:-2]) > .0) & ((v_res - v[2:]) > .0)
    dt_res, v_res = dt_res[v_diff], v_res[v_diff]
    idx = np.where(v_diff)[0] + 1
    return dt_res, v_res, idx


# def is_maxima(ts: pd.Series, idx_list: Sequence) -> Sequence:
#     """ Check whether a sequence of indices corresponds to maxima.
#
#         Input:
#             ts [pd.Series]: Input series
#             idx_list [Sequence]: list of locations to verify
#
#         Output:
#             res [Sequence]: output series of truth values
#     """
#     ts_diff = [False] * len(idx_list)
#     for i, idx in enumerate(idx_list):
#         loc = ts.index.get_loc(idx)
#         try:
#             if (ts.iat[loc] > ts.iat[loc - 1]) & (ts.iat[loc] > ts.iat[loc + 1]):
#                 ts_diff[i] = True
#         except IndexError:
#             pass
#     return ts_diff


def _find_ts_extrema(dt: np.ndarray, val: np.ndarray, w: int = 15) -> tuple:
    """ Find the signal points corresponding to maxima/minima of a underlying
        smoothed series. Return the unsorted maxima/minima and relative indexes.

        Input:
            dt [np.ndarray]: Input dates series
            val [np.ndarray]: Input values series
            w [int]: list of locations to verify (Default: 15)

        Output:
            max_i [tuple]: unsorted list of maxima numeric indices found
            min_i [tuple]: unsorted list of minima numeric indices found
    """
    s = _smooth(val, w=w)
    i_max = _find_maxima(dt, s)[2]
    i_min = _find_minima(dt, s)[2]

    # Search maxima/minima
    length = val.shape[0]
    # w_2 = (w + 1) // 2
    w_2 = w // 4  # This is somewhat arbitrary, let's see whether it works

    max_i = set()
    for i in i_max:
        low, high = max(i - w_2, 0), min(i + w_2 + 1, length)
        try:
            v = np.nanargmax(val[low:high]) + low
            max_i.add(v)
        except ValueError:
            # If we end up here it means that everything is NaN
            pass

    min_i = set()
    for i in i_min:
        low, high = max(i - w_2, 0), min(i + w_2 + 1, length)
        try:
            v = np.nanargmin(val[low:high]) + low
            min_i.add(v)
        except ValueError:
            # If we end up here it means that everything is NaN
            pass

    return tuple(max_i), tuple(min_i)


def _group_extrema(extrema: np.ndarray, tolerance: float = .05,
                   min_delta: float = .0025, dump: float = .75,
                   max_iter: int = 50) -> tuple:
    mean_p = np.nanmean(extrema)
    delta = tolerance * mean_p
    min_delta = min_delta * mean_p
    converged = False

    it, grp_list = 0, []
    while (not converged) & (it <= max_iter):
        it += 1
        grp_list = []
        # TODO: substitute loop with initial distance calculation
        for i, p_i in enumerate(extrema):
            high, low = p_i + delta, p_i - delta
            indexes = np.where(np.logical_and(extrema > low, extrema < high))[0]
            grp_list.append(indexes)

        converged = True
        # FIXME: vectorize?
        if delta > min_delta:
            for g in grp_list:
                if len(g) < 3:
                    continue
                v = np.tile(extrema[g], (len(g), 1))
                error = np.abs(v - v.T) - delta * .5
                if np.any(error > .0):
                    delta = max(min_delta, delta * dump)
                    converged = False
                    break

    eliminated = []
    # FIXME: vectorize?
    for i, g in enumerate(grp_list):
        if (len(g) == 1) or (i in eliminated):
            continue
        eliminated.extend([v for v in g if v != i])
    groups = [extrema[g] for i, g in enumerate(grp_list)
              if i not in eliminated]
    centers = np.array([g.mean() for g in groups])
    centers = np.unique(centers)

    return centers, converged, it, delta


def merge_sr(vola: float, groups: Sequence) -> Sequence:
    """ Remove redundant S/R lines from S/R groups. The groups must be supplied
        in order of priority. The first group is retained intact, the S/R lines
        in following groups are compared to the ones in previous groups. If a
        line falls in the confidence band of another S/R line generated using
        the daily return volatility, the line is deleted.

        Input:
            vola [float]: returns volatility
            groups [Sequence]: sequence of S/R groups in order of priority

        Output:
            res [Tuple[np.ndarray]]: S/R groups amended
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
            mask = (i < v[0, :count]) & (i > v[1, :count])
            if not np.any(mask):
                to_add.append(i)

        result.append(np.array(to_add))
        count += len(g)

    return tuple(result)


def search_sr(dt: np.ndarray, v: np.ndarray, w: int,
              **kwargs) -> np.ndarray:
    """ Search Support/Resistance lines.

        Input:
            dt [np.ndarray]: Input dates series
            val [np.ndarray]: Input values series
            w [int]: list of locations to verify

        Output:
            centers [np.ndarray]: array with group centers
    """
    max_i, min_i = _find_ts_extrema(dt, v, w=w)
    all_i = sorted(max_i + min_i)
    return _group_extrema(v[all_i], **kwargs)[0]
