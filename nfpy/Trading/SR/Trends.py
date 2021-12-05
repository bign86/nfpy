#
# Trends functions
# Functions to trends in time series such as extrema (maxima and minima),
# support/resistance lines, trendlines, wedges.
#

import numpy as np

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


def _find_ts_extrema(v: np.ndarray, w: int = 15) -> np.ndarray:
    """ Find the signal points corresponding to maxima/minima of a underlying
        smoothed series. Return the unsorted maxima/minima and relative indexes.

        Input:
            v [np.ndarray]: Input values series
            w [int]: list of locations to verify (Default: 15)

        Output:
            idx [tuple]: sorted list of maxima/minima indices
    """
    s = _smooth(v, w=w)
    s_pre = s[1:-1] - s[:-2]
    s_post = s[1:-1] - s[2:]
    i_min = np.where((s_pre < .0) & (s_post < .0))[0] + 1
    i_max = np.where((s_pre > .0) & (s_post > .0))[0] + 1

    w_2 = w // 4  # This is somewhat arbitrary, let's see whether it works
    stride = Math.rolling_window(v, 2 * w_2 + 1)
    idx = np.empty(i_max.shape[0] + i_min.shape[0], dtype=np.int)

    i_max = np.minimum(i_max - w_2, stride.shape[0] - 1)
    idx[:i_max.shape[0]] = np.nanargmax(stride[i_max, :], axis=1) + i_max

    i_min = np.minimum(i_min - w_2, stride.shape[0] - 1)
    idx[-i_min.shape[0]:] = np.nanargmin(stride[i_min, :], axis=1) + i_min

    return np.unique(idx)


def search_maxmin(dt: np.ndarray, v: np.ndarray, w: int, tol: float = 1) -> []:
    """ Search Support/Resistance lines using the maxima/minima of the prices
        given the rolling window.

        Input:
            dt [np.ndarray]: Input dates series
            val [np.ndarray]: Input values series
            w [int]: list of locations to verify
            tol [float]: multiplication factor to the volatility for grouping

        Output:
            centers [np.ndarray]: array with group centers
    """
    idx = _find_ts_extrema(v, w=w)
    sigma = float(np.nanstd(v[1:] / v[:-1] - 1))
    extrema = v[idx]

    sort_idx = np.argsort(extrema)
    sort_ext = extrema[sort_idx]
    diff = np.diff(sort_ext)

    mask_grp = np.empty_like(sort_ext, dtype=np.bool)
    mask_grp[0] = True
    mask_grp[1:] = diff > sort_ext[1:] * sigma * tol
    groups = np.cumsum(mask_grp)

    i = np.max(groups)
    centroids = np.empty(i)
    for n in range(i):
        centroids[n] = np.mean(sort_ext[groups == n+1])

    unsort = np.argsort(sort_idx[mask_grp])
    dates = dt[idx][sort_idx][mask_grp][unsort]

    return centroids[unsort], dates


def _calc_rolling_density(v: np.ndarray, w: int) -> np.ndarray:
    bins = w // 10
    v = Math.rolling_window(v, w)
    hist = np.empty((v.shape[1], bins))
    for i in v.shape[1]:
        hist[i, :] = np.histogram(v[:, i], bins=bins, normed=True)

    return hist


def search_density(dt: np.ndarray, v: np.ndarray, w: int, tol: float = 1) -> []:
    idx = _calc_rolling_density(v, w=w)
    return idx


def merge_sr(groups: [np.ndarray], vola: float) -> [np.ndarray]:
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
            all_in = np.any((i < v[0, :count]) & (i > v[1, :count]))
            if not all_in:
                to_add.append(i)
        result.append(np.array(to_add))
        count += len(g)

    return result


################################################################################
#                           OLD STUFF TO DELETE                                #
################################################################################

def _find_minima(v: np.ndarray) -> np.array:
    """ Find the minima of a series.

        Input:
            v [np.ndarray]: Input values series

        Output:
            idx [list]: list of numeric indices found
    """
    v_diff = ((v[1:-1] - v[:-2]) < .0) & ((v[1:-1] - v[2:]) < .0)
    return np.where(v_diff)[0] + 1


def _find_maxima(v: np.ndarray) -> np.array:
    """ Find the maxima of a series.

        Input:
            v [np.ndarray]: Input values series

        Output:
            idx [list]: list of numeric indices found
    """
    v_diff = ((v[1:-1] - v[:-2]) > .0) & ((v[1:-1] - v[2:]) > .0)
    return np.where(v_diff)[0] + 1


def search_sr_old(v: np.ndarray, w: int, **kwargs) -> np.ndarray:
    """ Search Support/Resistance lines.

        Input:
            dt [np.ndarray]: Input dates series
            val [np.ndarray]: Input values series
            w [int]: list of locations to verify

        Output:
            centers [np.ndarray]: array with group centers
    """
    max_i, min_i = _find_ts_extrema_old(v, w=w)
    all_i = sorted(max_i + min_i)
    return _group_extrema(
        v[all_i],
        tolerance=float(np.nanstd(v[1:] / v[:-1] - 1)),
        **kwargs
    )[0]


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
            indexes = np.where(
                np.logical_and(
                    extrema > p_i - delta,
                    extrema < p_i + delta
                )
            )[0]
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
    groups = [
        extrema[g] for i, g in enumerate(grp_list)
        if i not in eliminated
    ]
    centers = np.unique(
        np.array([
            g.mean() for g in groups
        ])
    )

    return centers, converged, it, delta


def _find_ts_extrema_old(val: np.ndarray, w: int = 15) -> tuple:
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
    i_max = _find_maxima(s)
    i_min = _find_minima(s)

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
