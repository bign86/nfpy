#
# Trends functions
# Functions to trends in time series such as extrema (maxima and minima),
# support/resistance lines, trendlines, wedges.
#

from typing import Sequence

import numpy as np
import pandas as pd

from nfpy.Tools import Utilities as Ut


def smooth(ts: pd.Series, w: int = 15) -> pd.Series:
    """ Smooth a time series.

        Input:
            ts [pd.Series]: time series to smooth
            w [int]: smoothing window (default: 15)

        Output:
            smooth [pd.Series]: smoothed time series
    """
    if w < 3:
        return ts.ffill()
    x = ts.ffill().values

    if x.shape[0] < w:
        raise ValueError("Input vector needs to be bigger than window size.")

    if w % 2 == 0:
        w = w + 1
    h = w // 2

    s = np.r_[x[w - 1:0:-1], x, x[-2:-w - 1:-1]]
    wgt = np.hamming(w)

    c = np.convolve(wgt / wgt.sum(), s, mode='valid')
    return pd.Series(c[h:-h], index=ts.index)


def find_minima(ts: pd.Series, idx_list: Sequence = None) -> tuple:
    """ Find the minima of a series.

        Input:
            ts [pd.Series]: Input series
            idx_list [Iterable]: list of locations to verify (default None)

        Output:
            res [pd.Series]: output series of minima
            idx [list]: list of numeric indices found
    """
    if idx_list is None:
        ts_diff = (ts < ts.shift(1)) & (ts < ts.shift(-1))
    else:
        # FIXME: vectorize?
        ts_diff = []
        for idx in idx_list:
            loc = ts.index.get_loc(idx)
            try:
                if (ts.iat[loc] < ts.iat[loc - 1]) & (ts.iat[loc] < ts.iat[loc + 1]):
                    ts_diff.append(idx)
            except IndexError:
                pass
    res = ts.loc[ts_diff]
    idx = [ts.index.get_loc(i) for i in res.index]
    return res, idx


def find_maxima(ts: pd.Series, idx_list: Sequence = None) -> tuple:
    """ Find the maxima of a series.

        Input:
            ts [pd.Series]: Input series
            idx_list [Iterable]: list of locations to verify (Default: None)

        Output:
            res [pd.Series]: output series of maxima
            idx [list]: list of numeric indices found
    """
    if idx_list is None:
        ts_diff = (ts > ts.shift(1)) & (ts > ts.shift(-1))
    else:
        # FIXME: vectorize?
        ts_diff = []
        for idx in idx_list:
            loc = ts.index.get_loc(idx)
            try:
                if (ts.iat[loc] > ts.iat[loc - 1]) & \
                        (ts.iat[loc] > ts.iat[loc + 1]):
                    ts_diff.append(idx)
            except IndexError:
                pass
    res = ts.loc[ts_diff]
    idx = [ts.index.get_loc(i) for i in res.index]
    return res, idx


def find_ts_extrema(ts: pd.Series, w: int = 15):
    """ Find the signal points corresponding to maxima/minima of a underlying
        smoothed series.

        Input:
            ts [pd.Series]: Input series
            w [int]: list of locations to verify (Default: 15)

        Output:
            max [pd.Series]: output series of maxima
            min [pd.Series]: output series of minima
            max_i [list]: list of maxima numeric indices found
            min_i [list]: list of minima numeric indices found
    """
    smoo = smooth(ts, w=w)  # .values
    _, i_max = find_maxima(smoo)
    _, i_min = find_minima(smoo)

    # Search maxima/minima
    val = ts.values
    length = len(val)
    # w_2 = (w + 1) // 2
    w_2 = w // 4  # This is somewhat arbitrary, let's see whether it works
    max_i, min_i = [], []
    for i in i_max:
        low, high = max(i - w_2, 0), min(i + w_2 + 1, length)
        try:
            v = np.nanargmax(val[low:high]) + low
            max_i.append(v)
        except ValueError:
            # If we end up here it means the everything is NaN
            pass
    max_i = Ut.ordered_unique(max_i)
    for i in i_min:
        low, high = max(i - w_2, 0), min(i + w_2 + 1, length)
        try:
            v = np.nanargmin(val[low:high]) + low
            min_i.append(v)
        except ValueError:
            # If we end up here it means the everything is NaN
            pass
    min_i = Ut.ordered_unique(min_i)
    return ts.iloc[max_i], ts.iloc[min_i], max_i, min_i


def group_extrema(ts, tolerance=.01, min_delta=.01, dump=.9, max_iter=50) -> tuple:
    return _group_extrema_dict(ts, tolerance, min_delta, dump, max_iter)


def _group_extrema_dict(ts, tolerance=.01, min_delta=.01, dump=.9, max_iter=50) -> tuple:
    pp = ts.values
    delta = tolerance * np.nanmean(pp)
    converged = False

    it, grp_dict = 0, {}
    while (not converged) & (it <= max_iter):
        it += 1
        grp_dict = {}
        # TODO: substitute loop with initial distance calculation
        for i, p_i in enumerate(pp):
            high, low = p_i + delta, p_i - delta
            grp_dict[i] = np.where(np.logical_and(pp > low, pp < high))[0]

        # length = [len(g) for g in groups.values()]
        converged = True
        # FIXME: vectorize?
        if delta > min_delta:
            for g in grp_dict.values():
                if len(g) < 3:
                    continue
                v = np.tile(pp[g], (len(g), 1))
                error = np.abs(v - v.T) - delta * .5
                if np.any(error > .0):
                    delta = max(min_delta, delta * dump)
                    converged = False
                    break

    eliminated = []
    # FIXME: vectorize?
    for i, item in enumerate(grp_dict.items()):
        k, g = item
        if (len(g) == 1) or (k in eliminated):
            continue
        eliminated.extend([v for v in g if v != i])
    groups = [ts.iloc[g] for k, g in grp_dict.items() if k not in eliminated]
    centers = [g.mean() for g in groups]

    return centers, groups, converged, it, delta
