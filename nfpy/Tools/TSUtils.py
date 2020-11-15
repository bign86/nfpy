#
# TSUtils
# Utilities functions to work on time series
#
from copy import deepcopy
from typing import Iterable, Union
import numpy as np
import pandas as pd


def skewness(ts: np.ndarray) -> float:
    """ Calculates the third standard moment. """
    ts_zm = ts - np.nanmean(ts)
    return np.power(ts_zm, 3) / (np.nanstd(ts) ** 3)


def kurtosis(ts: np.ndarray) -> float:
    """ Calculates the fourth standard moment. """
    ts_zm = ts - np.nanmean(ts)
    return np.power(ts_zm, 4) / (np.nanstd(ts) ** 4)


def series_momenta(ts: np.ndarray) -> tuple:
    """ Calculates first 4 momenta of the input series

        Output:
            mu [float]: mean
            var [float]: variance
            skewness [float]: skewness (third momentum)
            kurtosis [float]: kurtosis (fourth momentum)
    """
    mu = np.nanmean(ts)

    std = np.nanstd(ts)
    var = std * std
    ts_zm = ts - np.nanmean(ts)

    ts_exp = np.power(ts_zm, 3)
    std_exp = var * std
    skew = np.nanmean(ts_exp) / std_exp

    ts_exp = ts_exp * ts_zm
    std_exp = std_exp * std
    kurt = np.nanmean(ts_exp) / std_exp

    return mu, var, skew, kurt


def rolling_window(v: np.ndarray, w: int):
    """ Generate strides that simulate the rolling() function from pandas. """
    shape = v.shape[:-1] + (v.shape[-1] - w + 1, w)
    strides = v.strides + (v.strides[-1],)
    return np.lib.stride_tricks.as_strided(v, shape=shape, strides=strides)


def rolling_sum(v: np.ndarray, w):
    """ Compute the rolling sum of the input array.

        Input:
            v [np.ndarray]: input array
            w [int]: size of the rolling window

        Output:
            ret [np.ndarray]: rolling sum output array
    """
    ret = np.nancumsum(v, axis=0, dtype=float)
    # ret[:, n:] = ret[:, n:] - ret[:, :-n]
    # return ret[:, n - 1:]
    ret[w:] = ret[w:] - ret[:-w]
    return ret[w - 1:]


def rolling_mean(v: np.ndarray, w: int):
    """ Compute the rolling mean of the input array.

        Input:
            v [np.ndarray]: input array
            w [int]: size of the rolling window

        Output:
            ret [np.ndarray]: rolling mean output array
    """
    return rolling_sum(v, w) / w


def trim_ts(v: Union[None, np.ndarray], dt: np.ndarray,
            start: Union[np.datetime64, pd.Timestamp] = None,
            end: Union[np.datetime64, pd.Timestamp] = None) -> tuple:
    """ Replicates the use of Pandas .loc[] to slice a time series on a given
        pair of dates. Returns the sliced values array and dates array.

        Input:
            v [np.array]: value series to trim
            dt [np.array]: dates series to trim
            start [Union[np.datetime64, pd.Timestamp]]:
                trimming start date (Default None)
            end [Union[np.datetime64, pd.Timestamp]]:
                trimming end date (Default None)

        Output:
            v [np.array]: value series trimmed
            dt [np.array]: dates series trimmed
    """
    if start is None and end is None:
        return v, dt

    search = []
    if start:
        search.append(np.datetime64(start))
    if end:
        search.append(np.datetime64(end))
    idx = np.searchsorted(dt, search)

    if v is not None:
        v = deepcopy(v)
    dt = deepcopy(dt)

    if start and end:
        if v is not None:
            v = v[idx[0]:idx[1]]
        dt = dt[idx[0]:idx[1]]

    elif start:
        if v is not None:
            v = v[idx[0]:]
        dt = dt[idx[0]:]
    elif end:
        if v is not None:
            v = v[:idx[0]]
        dt = dt[:idx[0]]

    # v_ = None if v is None else v_
    return v, dt


def last_valid_index(v: np.ndarray) -> int:
    """ Find the index of the last non-nan value. Similar to the Pandas method
        last_valid_index().
    """
    i = -1
    while np.isnan(v[i]):
        i -= 1
    if -i > len(v):
        raise ValueError('The series is all nans')
    return len(v) + i


def dropna(v: np.ndarray, axis: int = 0) -> tuple:
    """ Drop NA from 2D input array.
    """
    if len(v.shape) == 1:
        mask = ~np.isnan(v)
        _v = v[mask]
    else:
        mask = ~np.any(np.isnan(v), axis=axis, keepdims=True)
        tile_sh = (v.shape[axis], 1) if axis == 0 else (1, v.shape[axis])
        mask = np.tile(mask, tile_sh)
        _v = v[mask]
        n = len(_v) // v.shape[axis]
        if axis == 0:
            _v = _v.reshape((v.shape[axis], n))
        else:
            _v = _v.reshape((n, v.shape[axis]))
    return _v, mask


def fillna(v: np.ndarray, n: float) -> np.ndarray:
    """ Fill nan in the input array with the supplied value. """
    mask = np.where(np.isnan(v))
    v[mask] = n
    return v


def ffill_cols(v: np.ndarray, n: float = 0):
    """ Forward fill nan with the last valid value column-wise. """
    mask = np.isnan(v)
    tmp = v[0].copy()
    v[0][mask[0]] = n
    mask[0] = False
    idx = np.where(~mask, np.arange(mask.shape[0])[:, None], 0)
    out = np.take_along_axis(v, np.maximum.accumulate(idx, axis=0), axis=0)
    v[0] = tmp
    return out


def ts_yield(dt: np.ndarray, ts: np.ndarray, base: np.ndarray,
             date: pd.Timestamp = None) -> float:
    """ Compute the yield of a time series with respect to a base series at a
        given date.

        Inputs:
            dt [np.array]: signal dates
            ts [np.array]: signal array at numerator
            base [np.array]: base series at denominator
            date [pd.Timestamp]: compute date (default None)

        Output:
            yield [float]: dividend yield
    """
    date = np.datetime64(date)
    ts, _ = trim_ts(ts, dt, end=date)
    base, _ = trim_ts(base, dt, end=date)

    idx_ts = last_valid_index(ts)
    idx_base = last_valid_index(base)
    return ts[idx_ts] / base[idx_base]


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


def find_minima(ts: pd.Series, idx_list: Iterable = None) -> pd.Series:
    """ Find the minima of a series.

        Input:
            ts [pd.Series]: Input series
            idx_list [Iterable]: list of locations to verify (default None)

        Output:
            _r [pd.Series]: output series of minima
    """
    if idx_list is None:
        ts_diff = (ts < ts.shift(1)) & (ts < ts.shift(-1))
        res = ts[ts_diff]
    else:
        ts_diff = []
        for idx in idx_list:
            loc = ts.index.get_loc(idx)
            try:
                if (ts.iat[loc] < ts.iat[loc - 1]) & (ts.iat[loc] < ts.iat[loc + 1]):
                    ts_diff.append(idx)
            except IndexError:
                pass
        res = ts.loc[ts_diff]
    return res


def find_maxima(ts: pd.Series, idx_list: Iterable = None) -> pd.Series:
    """ Find the maxima of a series.

        Input:
            ts [pd.Series]: Input series
            idx_list [Iterable]: list of locations to verify (Default None)

        Output:
            _r [pd.Series]: output series of maxima
    """
    if idx_list is None:
        ts_diff = (ts > ts.shift(1)) & (ts > ts.shift(-1))
        res = ts[ts_diff]
    else:
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
    return res


def find_ts_extrema(ts: pd.Series, w: int = 15):
    smoo = smooth(ts, w=w).values
    length = len(smoo)
    w_2 = w // 2

    i_max, i_min = [], []
    for i in range(-w_2, length, w):
        _last = min(i + w, length)
        i = max(i, 0)
        if i >= _last:
            break

        # Search smoothed max
        try:
            idx_max = np.nanargmax(smoo[i:_last]) + i
        except (KeyError, ValueError):
            # If we end up here it means the everything is NaN
            continue
        max_center = smoo[idx_max]
        try:
            if (max_center >= smoo[idx_max - 1]) & \
                    (max_center >= smoo[idx_max + 1]) & \
                    (idx_max not in i_max):
                i_max.append(idx_max)
        except IndexError:
            pass

        # Search smoothed min
        idx_min = np.nanargmin(smoo[i:_last]) + i
        min_center = smoo[idx_min]
        try:
            if (min_center <= smoo[idx_min - 1]) & \
                    (min_center <= smoo[idx_min + 1]) & \
                    (idx_min not in i_min):
                i_min.append(idx_min)
        except IndexError:
            pass

    # Search maxima/minima
    val = ts.values
    max_i = [np.nanargmax(val[max(i - w_2, 0):min(i + w_2 + 1, length)]) + i - w_2 for i in i_max]
    min_i = [np.nanargmin(val[max(i - w_2, 0):min(i + w_2 + 1, length)]) + i - w_2 for i in i_min]
    return ts.iloc[max_i], ts.iloc[min_i]
