#
# TSUtils
# Utilities functions to work on time series
#

from copy import deepcopy
from typing import Union
import numpy as np


def skewness(ts: np.ndarray, axis: int = 0) -> float:
    """ Calculates the third standard moment. """
    ts_zm = ts - np.nanmean(ts, axis=axis)
    return np.power(ts_zm, 3) / (np.nanstd(ts, axis=axis) ** 3)


def kurtosis(ts: np.ndarray, axis: int = 0) -> float:
    """ Calculates the fourth standard moment. """
    ts_zm = ts - np.nanmean(ts, axis=axis)
    return np.power(ts_zm, 4) / (np.nanstd(ts, axis=axis) ** 4)


def series_momenta(ts: np.ndarray, axis: int = 0) -> tuple:
    """ Calculates first 4 momenta of the input series

        Output:
            mu [float]: mean
            var [float]: variance
            skewness [float]: skewness (third momentum)
            kurtosis [float]: kurtosis (fourth momentum)
    """
    mu = np.nanmean(ts, axis=axis)

    std = np.nanstd(ts, axis=axis)
    var = std * std
    ts_zm = ts - np.nanmean(ts, axis=axis)

    ts_exp = np.power(ts_zm, 3)
    std_exp = var * std
    skew = np.nanmean(ts_exp, axis=axis) / std_exp

    ts_exp = ts_exp * ts_zm
    std_exp = std_exp * std
    kurt = np.nanmean(ts_exp, axis=axis) / std_exp

    return mu, var, skew, kurt


def rolling_window(v: np.ndarray, w: int):
    """ Generate strides that simulate the rolling() function from pandas. """
    shape = v.shape[:-1] + (v.shape[-1] - w + 1, w)
    strides = v.strides + (v.strides[-1],)
    return np.lib.stride_tricks.as_strided(v, shape=shape, strides=strides)


def rolling_sum(v: np.ndarray, w: int):
    """ Compute the rolling sum of the input array.

        Input:
            v [np.ndarray]: input array
            w [int]: size of the rolling window

        Output:
            ret [np.ndarray]: rolling sum output array
    """
    # ret[:, n:] = ret[:, n:] - ret[:, :-n]
    # return ret[:, n - 1:]
    ret = np.nancumsum(v, axis=0, dtype=float)
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
            start: np.datetime64 = None, end: np.datetime64 = None,
            axis: int = 0) -> tuple:
    """ Replicates the use of Pandas .loc[] to slice a time series on a given
        pair of dates. Returns the sliced values array and dates array.

        Input:
            v [np.ndarray]: value series to trim
            dt [np.ndarray]: dates series to trim
            start [np.datetime64]: trimming start date (Default None)
            end [np.datetime64]: trimming end date (Default None)
            axis [int]: axis along which to cut

        Output:
            v [np.ndarray]: value series trimmed
            dt [np.ndarray]: dates series trimmed
    """
    # Quick exit
    if ((start is None) and (end is None)) or (len(dt) == 0):
        return v, dt

    # If the dates array has length 1, return quickly
    if len(dt) == 1:
        t = dt[0]
        if ((start is not None) and (t < start)) or \
                ((end is not None) and (t > end)):
            return np.array([]), np.array([])
        else:
            return v, dt

    # Search the cut positions
    search = []
    if start:
        search.append(start)
    if end:
        search.append(end + np.timedelta64(1, 'D'))
    idx = np.searchsorted(dt, search)

    # Do not modify the input
    if v is not None:
        v = deepcopy(v)
    dt = deepcopy(dt)

    # Create the slice
    if start and end:
        slc = slice(idx[0], idx[1])
    elif start:
        slc = slice(idx[0], None)
    else:
        slc = slice(None, idx[0])
    slc_list = [slice(None)] * len(v.shape)
    slc_list[axis] = slc

    # Perform the slicing
    if v is not None:
        v = v[tuple(slc_list)]
    dt = dt[slc]

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
    elif len(v.shape) == 2:
        mask = ~np.any(np.isnan(v), axis=axis, keepdims=True)
        tile_sh = (v.shape[axis], 1) if axis == 0 else (1, v.shape[axis])
        mask = np.tile(mask, tile_sh)
        _v = v[mask]
        n = len(_v) // v.shape[axis]
        if axis == 0:
            _v = _v.reshape((v.shape[axis], n))
        else:
            _v = _v.reshape((n, v.shape[axis]))
    else:
        raise NotImplementedError('3D+ arrays not supported')

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
             date: np.datetime64 = None) -> float:
    """ Compute the yield of a time series with respect to a base series at a
        given date.

        Inputs:
            dt [np.ndarray]: signal dates
            ts [np.ndarray]: signal array at numerator
            base [np.ndarray]: base series at denominator
            date [np.datetime64]: compute date (default None)

        Output:
            yield [float]: dividend yield
    """
    ts, _ = trim_ts(ts, dt, end=date)
    base, _ = trim_ts(base, dt, end=date)

    idx_ts = last_valid_index(ts)
    idx_base = last_valid_index(base)
    return ts[idx_ts] / base[idx_base]
