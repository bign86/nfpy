#
# TSUtils
# Utilities functions to work on time series
#

from typing import Iterable, Union
import numpy as np
import pandas as pd


def skewness(ts: np.array) -> float:
    """ Calculates the third standard moment. """
    ts_zm = ts - ts.nanmean()
    return np.power(ts_zm, 3) / (ts.nanstd() ** 3)


def kurtosis(ts: np.array) -> float:
    ts_zm = ts - ts.nanmean()
    return np.power(ts_zm, 4) / (ts.nanstd() ** 4)


def series_momenta(ts: np.array) -> tuple:
    """ Calculates first 4 momenta of the input series

        Output:
            mu [float]: mean
            var [float]: variance
            skewness [float]: skewness (third momentum)
            kurtosis [float]: kurtosis (fourth momentum)
    """
    mu = ts.nanmean()

    std = ts.nanstd()
    var = std * std
    ts_zm = ts - ts.nanmean()

    ts_exp = np.power(ts_zm, 3)
    std_exp = var * std
    skew = ts_exp.nanmean() / std_exp

    ts_exp = ts_exp * ts_zm
    std_exp = std_exp * std
    kurt = ts_exp.nanmean() / std_exp

    return mu, var, skew, kurt


def rolling_window(v: np.ndarray, w):
    shape = v.shape[:-1] + (v.shape[-1] - w + 1, w)
    strides = v.strides + (v.strides[-1],)
    return np.lib.stride_tricks.as_strided(v, shape=shape, strides=strides)


def rolling_sum(v: np.ndarray, w):
    ret = np.cumsum(v, axis=0, dtype=float)
    # ret[:, n:] = ret[:, n:] - ret[:, :-n]
    # return ret[:, n - 1:]
    ret[w:] = ret[w:] - ret[:-w]
    return ret[w - 1:]


def rolling_mean(v: np.array, w: int):
    # ret = np.cumsum(v, dtype=float)
    # ret[w:] = ret[w:] - ret[:-w]
    # return ret[w - 1:] / w
    return rolling_sum(v, w) / w


def trim_ts(v: np.array, dt: np.array,
            start: Union[np.datetime64, pd.Timestamp] = None,
            end: Union[np.datetime64, pd.Timestamp] = None) -> tuple:
    """ Replicates the use of Pandas .loc[] to slice a time series on a given
        pair of dates. Returns the sliced values array and dates array.
    """
    if start is None and end is None:
        return v, dt

    search = []
    if start:
        search.append(np.datetime64(start))
    if end:
        search.append(np.datetime64(end))
    idx = np.searchsorted(dt, search)

    if start and end:
        v = v[idx[0]:idx[1]]
        dt = dt[idx[0]:idx[1]]
    elif start:
        v = v[idx[0]:]
        dt = dt[idx[0]:]
    elif end:
        v = v[:idx[0]]
        dt = dt[:idx[0]]
    return v, dt


def last_valid_index(v: np.array) -> int:
    """ Find the index of the last non-nan value. Equal to the Pandas method
        last_valid_index().
    """
    i = -1
    while np.isnan(v[i]):
        i -= 1
    if -i > len(v):
        raise ValueError('The series is all nans')
    return len(v) + i


def dropna(v: np.array, dt: np.array = None) -> tuple:
    """ Drop NA from input array. A second array can be supplied that will be
        kept aligned with the principal one.
    """
    idx = np.argwhere(np.isnan(v))
    _v = np.delete(v, idx)
    _dt = np.delete(dt, idx) if dt is not None else None
    return _v, _dt


def ts_yield(ts: np.array, dt: np.array, base: pd.Series, dt_base: np.array,
             date: pd.Timestamp = None) -> float:
    """ Compute the yield of a time series with respect to a base series at a
        given date.

        Inputs:
            ts [np.array]: signal array at numerator
            dt [np.array]: signal dates
            base [np.array]: base series at denominator
            dt_base [np.array]: base dates
            date [pd.Timestamp]: compute date (default None)

        Output:
            yield [float]: dividend yield
    """
    date = np.datetime64(date)
    ts, dt = trim_ts(ts, dt, end=date)
    base, dt_base = trim_ts(base, dt_base, end=date)

    idx_ts = last_valid_index(ts)
    idx_base = last_valid_index(base)
    return ts[idx_ts] / base[idx_base]


# def ts_yield_pd(ts,base: pd.Series,
#              date: pd.Timestamp = None) -> float:
#     """ Compute the yield of a time series with respect to a base series at a
#         given date.
#
#         Inputs:
#             ts [np.array]: signal array at numerator
#             dt [np.array]: signal dates
#             base [np.array]: base series at denominator
#             dt_base [np.array]: base dates
#             date [pd.Timestamp]: compute date (default None)
#
#         Output:
#             yield [float]: dividend yield
#     """
#     ts = trim_ts(ts, end=date)
#     base = trim_ts(base, end=date)
#
#     idx_div = ts.last_valid_index()
#     idx_p = base.last_valid_index()
#     return ts.at[idx_div] / base.at[idx_p]


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
            idx_list [Iterable]: list of locations to verify (default None)

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
                if (ts.iat[loc] > ts.iat[loc - 1]) & (ts.iat[loc] > ts.iat[loc + 1]):
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
