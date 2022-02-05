#
# TSUtils_
# Utilities functions to work on time series
#

from copy import deepcopy
import numpy as np
from typing import Optional

from nfpy.Tools import Exceptions as Ex


def dropna(v: np.ndarray, axis: int = 0) -> tuple:
    """ Drop NA from 2D input array. NOT inplace. """
    if len(v.shape) == 1:
        mask = ~np.isnan(v)
        _v = v[mask]
    elif len(v.shape) == 2:
        mask = ~np.any(np.isnan(v), axis=axis, keepdims=True)
        tile_sh = (v.shape[axis], 1) if axis == 0 else (1, v.shape[axis])
        _v = v[np.tile(mask, tile_sh)]
        n = len(_v) // v.shape[axis]
        if axis == 0:
            _v = _v.reshape((v.shape[axis], n))
        else:
            _v = _v.reshape((n, v.shape[axis]))
    else:
        raise Ex.ShapeError('3D+ arrays not supported')

    return _v, mask


def fillna(v: np.ndarray, n: float, inplace=False) -> np.ndarray:
    """ Fill nan in the input array with the supplied value. """
    mask = np.where(np.isnan(v))
    if not inplace:
        v = v.copy()
    v[mask] = n
    return v


# TODO: implement the inplace option
def ffill_cols(v: np.ndarray, n: float = 0, inplace=False) -> np.ndarray:
    """ Forward fill nan with the last valid value column-wise.

        Input:
            v [np.ndarray]: input array either 1-D or 2-D
            n [float]: fill up value for NaNs appearing at the beginning
                       of the data series.
            inplace [bool]: do it in-place (Default: False)

        Output:
            out [np.ndarray]: array with NaNs filled column-wise
    """
    # FIXME: this involves a copy in np.flatten(). In general, bad way to take
    #        into account dimensionality.
    flatten = False
    if len(v.shape) == 1:
        v = v[:, None]
        flatten = True
    mask = np.isnan(v)
    tmp = v[0].copy()
    v[0][mask[0]] = n
    mask[0] = False
    idx = np.where(~mask, np.arange(mask.shape[0])[:, None], 0)
    out = np.take_along_axis(v, np.maximum.accumulate(idx, axis=0), axis=0)
    v[0] = tmp

    if flatten:
        out = out.flatten()
    return out


def last_valid_index(v: np.ndarray, start: int = None) -> int:
    """ Find the index of the last non-nan value. Similar to the Pandas method
        last_valid_index(). It can be used with 1D arrays only.

        Input:
            v [np.ndarray]: input series
            start [int]: starting index

        Output:
            i [int]: last valid index
    """
    if len(v.shape) > 1:
        raise Ex.ShapeError('Only 1D arrays supported')

    i = v.size - 1 \
        if start is None \
        else min(start, v.size - 1)

    while np.isnan(v[i]) and (i >= 0):
        i -= 1
    if i < 0:
        raise ValueError('The series is all nans')
    return i


def last_valid_value(v: np.ndarray, dt: np.ndarray = None,
                     t0: np.datetime64 = None) -> tuple[float, int]:
    """ Find the last valid value at a date <= t0. It can be used with 1D arrays
        only.

        Input:
            v [np.ndarray]: series of prices
            dt [np.ndarray]: series of price dates (default None)
            t0 [np.datetime64]: reference date (default None)

        Output:
            val [float]: value of the series at or before t0
            idx [int]: corresponding index
    """
    if len(v.shape) > 1:
        raise Ex.ShapeError('Only 1D arrays supported')

    if t0:
        pos = np.searchsorted(dt, t0, side='right')
        v = v[:pos]
    idx = last_valid_index(v)
    return float(v[idx]), idx


def next_valid_index(v: np.ndarray, start: int = 0) -> int:
    """ Find the index of the next non-nan value starting from the given index.
        It can be used with 1D arrays only.

        Input:
            v [np.ndarray]: input series
            start [int]: starting index (default 0)

        Output:
            i [int]: next valid index
    """
    if len(v.shape) > 1:
        raise Ex.ShapeError('Only 1D arrays supported')

    i = start
    n = len(v)
    while (i < n) and np.isnan(v[i]):
        i += 1
    if i == n:
        raise ValueError('The series is all nans')
    return i


def next_valid_value(v: np.ndarray, dt: np.ndarray = None,
                     t0: np.datetime64 = None) -> tuple[float, int]:
    """ Find the next valid value starting from the given index. It can be used
        with 1D arrays only.

        Input:
            v [np.ndarray]: series of prices
            dt [np.ndarray]: series of price dates (Default None)
            t0 [np.datetime64]: reference date (Default None)

        Output:
            val [float]: value of the series at or after t0
            idx [int]: corresponding index
    """
    if len(v.shape) > 1:
        raise Ex.ShapeError('Only 1D arrays supported')

    if t0:
        pos = np.searchsorted(dt, t0, side='right')
        v = v[:pos]
    idx = next_valid_index(v)
    return float(v[idx]), idx


def rolling_mean(v: np.ndarray, w: int) -> np.ndarray:
    """ Compute the rolling mean of the input array.

        Input:
            v [np.ndarray]: input array
            w [int]: size of the rolling window

        Output:
            ret [np.ndarray]: rolling mean output array
    """
    # FIXME: shouldn't nanmean() take care of the nans problem?
    v = v.copy()
    d, idx = last_valid_value(v)
    v[idx + 1:] = d
    return np.nanmean(rolling_window(v, w), axis=1)


def rolling_sum(v: np.ndarray, w: int) -> np.ndarray:
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


def rolling_window(v: np.ndarray, w: int) -> np.ndarray:
    """ Generate strides that simulate the rolling() function from pandas. """
    shape = v.shape[:-1] + (v.shape[-1] - w + 1, w)
    strides = v.strides + (v.strides[-1],)
    return np.lib.stride_tricks.as_strided(v, shape=shape, strides=strides)


def search_trim_pos(dt: np.ndarray, start: np.datetime64 = None,
                    end: np.datetime64 = None) -> Optional[slice]:
    if len(dt.shape) > 1:
        raise Ex.ShapeError('Only 1D arrays supported')

    # Quick exit
    if ((start is None) and (end is None)) or (len(dt) == 0):
        return slice(None, None)

    # If the dates array has length 1, return quickly
    if len(dt) == 1:
        t = dt[0]
        if ((start is not None) and (t < start)) or \
                ((end is not None) and (t > end)):
            return None
        else:
            return slice(None, None)

    # Search the cut positions
    i0, i1 = None, None
    if start:
        i0 = np.searchsorted(dt, start, side='left')
    if end:
        i1 = np.searchsorted(dt, end + np.timedelta64(1, 'D'), side='left')

    return slice(i0, i1)


def trim_ts(v: Optional[np.ndarray], dt: np.ndarray,
            start: Optional[np.datetime64] = None,
            end: Optional[np.datetime64] = None, axis: int = 0) \
        -> tuple[Optional[np.ndarray], np.ndarray]:
    """ Replicates the use of Pandas .loc[] to slice a time series on a given
        pair of dates. Returns the sliced values array and dates array NOT in
        place.

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
    if len(dt.shape) > 1:
        raise Ex.ShapeError('The dates array must be 1D')

    slice_obj = search_trim_pos(dt, start, end)

    # Quick exit
    if slice_obj is None:
        return None, np.array([])

    # Do not modify the input
    if v is not None:
        v = deepcopy(v)
    dt = deepcopy(dt)

    # Perform the slicing
    if v is not None:
        slc_list = [slice(None)] * len(v.shape)
        slc_list[axis] = slice_obj
        v = v[tuple(slc_list)]

    return v, dt[slice_obj]
