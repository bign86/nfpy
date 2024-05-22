#
# TSUtils_
# Utilities functions to work on time series
#

from copy import deepcopy
import cutils
import numpy as np
import scipy.signal as sig
from typing import Optional

import nfpy.IO.Utilities as Ut
from nfpy.Tools import Exceptions as Ex


def dropna(v: np.ndarray, axis: int = 0) -> tuple:
    """ Drop NA from 1D or 2D input array. NOT inplace.

        Input:
            v [np.ndarray]: input array
            axis [int]: apply along axis (default: 0)

        Ouput:
            arr [np.ndarray]: output array w/o NaNs
            mask [np.ndarray]: boolean mask of not-NaN values
    """
    Ut.print_deprecation('Math.dropna() -> cutils.dropna()')
    if len(v.shape) == 1:
        mask = ~np.isnan(v)
        _v = v[mask]
    elif len(v.shape) == 2:
        mask = ~np.any(np.isnan(v), axis=axis, keepdims=True)

        tile_sh = [1, 1]
        tile_sh[axis] = v.shape[axis]
        _v = v[np.tile(mask, tile_sh)]
        n = len(_v) // v.shape[axis]

        v_sh = [n, n]
        v_sh[axis] = v.shape[axis]
        _v = _v.reshape(v_sh)
        mask = mask.reshape((max(mask.shape),))
    else:
        raise Ex.ShapeError('dropna(): 3D+ arrays not supported')

    return _v, mask


# TODO: implement the inplace option
def ffill_cols(v: np.ndarray, n: float = 0, inplace=False) -> np.ndarray:
    """ Forward fill nan with the last valid value column-wise.

        Input:
            v [np.ndarray]: input array either 1-D or 2-D
            n [float]: fill up value for NaNs appearing at the beginning
                of the data series.
            inplace [bool]: do it in-place (default: False)

        Output:
            out [np.ndarray]: array with NaNs filled column-wise
    """
    Ut.print_deprecation('Math.ffill_cols() -> cutils.ffill()')
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


def fillna(v: np.ndarray, n: float, inplace=False) -> np.ndarray:
    """ Fill nan in the input array with the supplied value. """
    Ut.print_deprecation('Math.fillna() -> cutils.fillna()')
    mask = np.where(np.isnan(v))
    if not inplace:
        v = v.copy()
    v[mask] = n
    return v


def find_relative_extrema(v: np.ndarray, order: int) \
        -> tuple[np.ndarray, np.ndarray]:
    """ Finds the sorted indexes corresponding to maxima/minima of a series.

        Input:
            v [np.ndarray]: Input values series

        Output:
            idx [np.ndarray]: sorted list of maxima/minima indices
            flags [np.ndarray]: sorted list of maxima/minima flags.
                maxima=True, minima=False
    """
    idx_max = sig.argrelextrema(v, np.greater, order=order, mode='clip')[0]
    idx_min = sig.argrelextrema(v, np.less, order=order, mode='clip')[0]

    idx = np.concatenate((idx_max, idx_min))
    flags = np.empty(idx.shape[0], dtype=bool)
    flags[:idx_max.shape[0]] = True
    flags[idx_max.shape[0]:] = False

    # Calculate returned quantities
    sorting = np.argsort(idx)
    idx = idx[sorting]
    flags = flags[sorting]

    return idx, flags


def last_valid_value(v: np.ndarray, dt: Optional[np.ndarray] = None,
                     t0: Optional[np.datetime64] = None) -> tuple[float, int]:
    """ Find the last valid value at a date <= t0. It can be used with 1D arrays
        only.

        Input:
            v [np.ndarray]: series of prices
            dt [Optional[np.ndarray]]: series of price dates (default: None)
            t0 [Optional[np.datetime64]]: reference date (default: None)

        Output:
            val [float]: value of the series at or before t0
            idx [int]: corresponding index

        Exceptions:
            ShapeError: if array is not 1D or 2D
            ValueError: if the series is all nans
    """
    if len(v.shape) > 1:
        raise Ex.ShapeError('Math.last_valid_value(): only 1D arrays supported')

    if t0:
        if dt is None:
            raise ValueError('Math.last_valid_value(): to constrain the search with t0 you need to pass the array of dates')
        pos = np.searchsorted(dt, t0, side='right')
        v = v[:pos+1]

    idx = cutils.last_valid_index(v, 0, 0, v.shape[0] - 1)
    return float(v[idx]), idx


def next_valid_value(v: np.ndarray, dt: Optional[np.ndarray] = None,
                     t0: Optional[np.datetime64] = None) -> tuple[float, int]:
    """ Find the next valid value starting from the given index. It can be used
        with 1D arrays only.

        Input:
            v [np.ndarray]: series of prices
            dt [Optional[np.ndarray]]: series of price dates (default: None)
            t0 [Optional[np.datetime64]]: reference date (default: None)

        Output:
            val [float]: value of the series at or after t0
            idx [int]: corresponding index

        Exceptions:
            ShapeError: if array is not 1D or 2D
            ValueError: if the series is all nans
    """
    if len(v.shape) > 1:
        raise Ex.ShapeError('Math.next_valid_value(): only 1D arrays supported')

    if t0:
        if dt is None:
            raise ValueError('Math.next_valid_value(): to constrain the search with t0 you need to pass the array of dates')
        pos = np.searchsorted(dt, t0, side='right')
        v = v[pos:]

    idx = cutils.next_valid_index(v, 0, 0, v.shape[0] - 1)
    return float(v[idx]), idx


def search_trim_pos(dt: np.ndarray, start: Optional[np.datetime64] = None,
                    end: Optional[np.datetime64] = None) -> Optional[slice]:
    """ Replicates the use of Pandas .loc[] to slice a time series on a given
        pair of dates. Returns the sliced values array and dates array NOT in
        place.

        Input:
            dt [np.ndarray]: dates series to trim
            start [Optional[np.datetime64]]: trimming start date (default: None)
            end [Optional[np.datetime64]]: trimming end date (default: None)

        Output:
            slc [slice]: slice object
    """
    if len(dt.shape) > 1:
        raise Ex.ShapeError('search_trim_pos(): Only 1D arrays supported')

    # Quick exit
    if ((start is None) and (end is None)) or (dt.shape[0] == 0):
        return slice(None, None)

    # If the dates array has length 1, return quickly
    if dt.shape[0] == 1:
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
        # i1 = np.searchsorted(dt, end + np.timedelta64(1, 'D'), side='left')
        i1 = np.searchsorted(dt, end, side='right')

    return slice(i0, i1)


def smooth(ts: np.ndarray, w: int) -> np.ndarray:
    """ Smooth a time series over a window.

        Input:
            ts [np.ndarray]: time series to smooth
            w [int]: smoothing window

        Output:
            smooth [np.ndarray]: smoothed time series
    """
    if w < 2:
        return ts
    elif ts.shape[0] < w:
        raise ValueError("Input vector needs to be bigger than window size.")

    if w % 2 == 0:
        w = w + 1
    h = w // 2

    s = np.r_[ts[w - 1:0:-1], ts, ts[-2:-w - 1:-1]]
    wgt = np.hamming(w)

    c = np.convolve(wgt / wgt.sum(), s, mode='valid')
    return c[h:-h]


def trim_ts(dt: np.ndarray, v: Optional[np.ndarray],
            start: Optional[np.datetime64] = None,
            end: Optional[np.datetime64] = None, axis: int = 0) \
        -> tuple[Optional[np.ndarray], np.ndarray]:
    """ Replicates the use of Pandas .loc[] to slice a time series on a given
        pair of dates. Returns the sliced values array and dates array NOT in
        place.

        Input:
            dt [np.ndarray]: dates series to trim
            v [Optional[np.ndarray]]: value series to trim
            start [Optional[np.datetime64]]: trimming start date (default: None)
            end [Optional[np.datetime64]]: trimming end date (default: None)
            axis [int]: axis along which to cut

        Output:
            v [np.ndarray]: value series trimmed
            dt [np.ndarray]: dates series trimmed
    """
    if len(dt.shape) > 1:
        raise Ex.ShapeError('trim_ts(): The dates array must be 1D')

    slice_obj = search_trim_pos(dt, start, end)

    # Quick exit
    if slice_obj is None:
        return None, np.array([])

    # Do not modify the input and perform the slicing
    dt = deepcopy(dt)

    if v is not None:
        v = deepcopy(v)
        slc_list = [slice(None)] * len(v.shape)
        slc_list[axis] = slice_obj
        v = v[tuple(slc_list)]

    return v, dt[slice_obj]
