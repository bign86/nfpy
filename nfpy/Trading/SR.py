#
# S/R finding
# Algorithms to find Support/Resistance levels in a bulk form.
#

import cutils
import numpy as np
from typing import (Optional, Sequence)

from nfpy.Assets import get_af_glob
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


def _search_centroids(ts: np.ndarray, flags: np.ndarray, tol: float,
                      dt: Optional[np.ndarray] = None) -> tuple:
    """ S/R centroid search. """
    mask = flags != 0
    if np.sum(mask) == 0:
        return np.array([]), None

    extrema = ts[mask]

    sort_idx = np.argsort(extrema)
    sort_ext = extrema[sort_idx]
    diff = np.diff(sort_ext)

    ret = ts[1:] / ts[:-1] - 1.
    ret[ret == np.inf] = .0
    sigma = float(np.nanstd(ret))

    mask_grp = np.empty_like(sort_ext, dtype=np.bool_)
    mask_grp[0] = True
    mask_grp[1:] = diff > sort_ext[1:] * sigma * tol
    groups = np.cumsum(mask_grp)

    i = np.max(groups)
    centroids = np.empty(i)
    for n in range(i):
        centroids[n] = np.mean(sort_ext[groups == n + 1])

    unsort = np.argsort(sort_idx[mask_grp])

    dates = None
    if dt is not None:
        dates = dt[flags][sort_idx][mask_grp][unsort]
    return centroids[unsort], dates


def _search_pivots(p: np.ndarray, thrs: float) -> np.ndarray:
    """ S/R search using the pivot levels algorithm. """
    up_thrs = 1. + thrs
    down_thrs = 1. - thrs

    flags = np.zeros(p.shape, dtype=int)
    start_idx = cutils.next_valid_index(p)

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

    last_idx = cutils.last_valid_index(p)
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
    if to_del.shape[0] > 0:
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


def get_pivot(dt: np.ndarray, p: np.ndarray, thrs: float) -> tuple:
    """ Find the pivot dates and prices.

        Input:
            dt [np.ndarray]: input dates series
            ts [np.ndarray]: input values series
            thrs [float]: return threshold

        Output:
            dates [np.ndarray]: array of pivot dates
            prices [np.ndarray]: array of pivot prices
    """
    flags = _search_pivots(p, thrs)
    mask = flags != 0
    return dt[mask], p[mask]


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


def sr_pivot(ts: np.ndarray, thrs: float, tol: float = 1.,
             dt: Optional[np.ndarray] = None) -> tuple:
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
        ts,
        _search_pivots(ts, thrs),
        tol, dt
    )


def sr_smooth(ts: np.ndarray, w: int, tol: float = 1.,
              dt: Optional[np.ndarray] = None) -> tuple:
    """ Search Support/Resistance lines using the maxima/minima of the smoothed
        price curve given a rolling window.

        Input:
            dt [np.ndarray]: input dates series
            ts [np.ndarray]: input values series
            w [int]: smoothing window length
            tol [float]: multiplication factor to the volatility for grouping

        Output:
            centers [np.ndarray]: array of S/R lines
            dates [np.ndarray]: array of S/R start dates
    """
    return _search_centroids(
        ts,
        _search_smooth(ts, w),
        tol, dt
    )


class SRBreachEngine(object):
    """ Class to perform S/R lines breach checks. """

    def __init__(self, ts: np.ndarray, check_w: int, tol: float,
                 mode: str = 'smooth', w: Optional[Sequence[int]] = None,
                 thrs: Optional[Sequence[float]] = None):
        """ Construct a new instance.

            Input:
                ts [np.ndarray]: input values series
                check_w [int]: how far in history to perform the check
                tol [float]: multiplication factor to the volatility for grouping
                mode [str]: methodology, 'smooth' or 'pivot' (default smooth)
                w [Optional[Sequence[int]]]: for mode=smooth, the list of window
                    length for the smoothing
                thrs [Optional[Sequence[int]]]: for mode=pivot, return threshold
                    to determine the pivot
        """
        self._ts = cutils.ffill(ts)

        self._check_w = check_w
        self._mode = mode
        self._w = w
        self._thrs = thrs
        self._tol = tol

        if self._mode == 'smooth':
            if w is None:
                raise ValueError(f'SRBreach(): you must give a window length for {self._mode}')
        elif self._mode == 'pivot':
            if thrs is None:
                raise ValueError(f'SRBreach(): you must give a threshold for {self._mode}')
        else:
            raise ValueError(f'SRBreach(): {self._mode} not recognized')

        self._vola = .0
        self._breaches = []
        self._is_calculated = False

    def get(self, triggers_only: bool = False) -> list:
        if not self._is_calculated:
            self._check_breaches()
        if triggers_only:
            return list(filter(lambda v: v[2] != '', self._breaches))
        else:
            return self._breaches

    def _check_breaches(self) -> None:
        if self._mode == 'smooth':
            # TODO: why? WHY???
            #    probably because like this is not possible to trigger an S/R
            #    before it is generated.
            test_ts = self._ts[:-self._check_w]
            all_sr = [
                sr_smooth(test_ts, w, self._tol)[0]
                for w in self._w
            ]
        else:  # mode == 'pivot'
            all_sr = [
                sr_pivot(self._ts, th, self._tol)[0]
                for th in self._thrs
            ]

        all_sr = [v for v in all_sr if v.shape[0] > 0]

        if len(all_sr) == 0:
            return

        ts_0 = Math.next_valid_value(self._ts[-self._check_w:])[0]
        ts_t = Math.last_valid_value(self._ts)[0]

        ret = cutils.ret_nans(self._ts, False)
        vola = float(np.nanstd(ret))
        # TODO: add input parameter for this
        ts_vola = 1.65 * vola * ts_t

        all_sr = np.concatenate(merge_sr(all_sr, vola))

        # Logic of breaches
        signals = []
        for sr in all_sr:
            status = ''
            if ts_0 <= sr:
                type_ = 'R'
                if abs(ts_t - sr) < ts_vola:
                    status = 'testing'
                elif ts_t > sr:
                    status = 'breach'
            else:
                type_ = 'S'
                if abs(ts_t - sr) < ts_vola:
                    status = 'testing'
                elif ts_t < sr:
                    status = 'breach'
            signals.append((type_, sr, status))

        self._breaches = signals
        self._is_calculated = True


def SRBreach(uid: str, check_w: int, tol: float, mode: str = 'smooth',
             w: Optional[Sequence[int]] = None,
             thrs: Optional[Sequence[float]] = None,
             triggers_only: bool = False) -> list:
    return SRBreachEngine(
        get_af_glob().get(uid).prices.to_numpy(),
        check_w=check_w, tol=tol, mode=mode, w=w, thrs=thrs
    ).get(triggers_only=triggers_only)
