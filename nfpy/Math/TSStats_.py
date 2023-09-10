#
# TSStats_
# Low level functions for time series to Cythonize
#

import cutils
import numpy as np
from typing import Optional

from nfpy.Tools import (Exceptions as Ex)

from .TSUtils_ import (search_trim_pos)


def correlation(dt: np.ndarray, ts: np.ndarray, bmk: np.ndarray,
                start: Optional[np.datetime64] = None,
                end: Optional[np.datetime64] = None) -> np.ndarray:
    """ Calculates the correlation between a series and a benchmark.

        Input:
            dt [np.ndarray]: dates time series
            ts [np.ndarray]: equity or other series under analysis
            bmk [np.ndarray]: reference benchmark time series
            start [Optional[np.datetime64]]: start date of the series (Default: None)
            end [Optional[np.datetime64]]: end date of the series excluded (Default: None)

        Output:
            corr [np.ndarray]: matrix of correlation coefficients
    """
    if (dt.shape != ts.shape != bmk.shape) and len(dt.shape) > 1:
        raise Ex.ShapeError('The series must have the same length')

    slc = search_trim_pos(dt, start=start, end=end)
    v = cutils.dropna(
        np.vstack((ts[slc], bmk[slc])),
        1
    )

    return np.corrcoef(v)


def kurtosis(ts: np.ndarray, axis: int = 0) -> float:
    """ Calculates the kurtosis - fourth standard moment.

        Input:
            ts [np.ndarray]: value series
            axis [int]: axis to calculate along (Default: 0)

        Output:
            kurt [Union[float, np.ndarray]]: kurtosis
    """
    ts_zm = ts - np.nanmean(ts, axis=axis)
    return np.power(ts_zm, 4) / (np.nanstd(ts, axis=axis) ** 4)


def mean_ad(v: np.ndarray, axis: Optional[int] = 0):
    """ Calculates the Mean Average Deviation of the series.

        Input:
            v [np.ndarray]: values array
            axis [Optional[int]]: axis, only up to 2D supported

        Ouput:
            mad [np.ndarray]: calculated array of mad
    """
    if axis == 0:
        dmean = v - np.nanmean(v, axis=0)
    else:
        dmean = (v.T - np.nanmean(v, axis=1)).T

    return np.nanmean(
        np.abs(dmean),
        axis=axis
    )


def median_ad(v: np.ndarray, axis: Optional[int] = 0):
    """ Calculates the Median Average Deviation of the series.

        Input:
            v [np.ndarray]: values array
            axis [Optional[int]]: axis, only up to 2D supported

        Ouput:
            mad [np.ndarray]: calculated array of mad
    """
    if axis == 0:
        dmed = v - np.nanmedian(v, axis=0)
    else:
        dmed = (v.T - np.nanmedian(v, axis=1)).T

    return np.nanmedian(
        np.abs(dmed),
        axis=axis
    )


def rolling_mean(v: np.ndarray, w: int) -> np.ndarray:
    """ Compute the rolling mean of the input array.

        Input:
            v [np.ndarray]: input array
            w [int]: size of the rolling window

        Output:
            ret [np.ndarray]: rolling mean output array of length len(v) - w + 1
    """
    return np.nanmean(rolling_window(v, w), axis=1)


def rolling_mad(v: np.ndarray, w: int) -> np.ndarray:
    """ Compute the rolling mean average deviation of the input array.

        Input:
            v [np.ndarray]: input array
            w [int]: size of the rolling window

        Output:
            ret [np.ndarray]: rolling mad output array of length len(v) - w + 1
    """

    ma = np.nanmean(rolling_window(v, w), axis=1)
    ma = np.r_[[ma[0]]*(w-1), ma]
    dmean = np.abs(v - ma)
    return np.nanmean(rolling_window(dmean, w), axis=1)


def rolling_median(v: np.ndarray, w: int) -> np.ndarray:
    """ Compute the rolling median of the input array.

        Input:
            v [np.ndarray]: input array
            w [int]: size of the rolling window

        Output:
            ret [np.ndarray]: rolling median output array of length
                len(v) - w + 1
    """
    return np.nanmedian(rolling_window(v, w), axis=1)


def rolling_median_ad(v: np.ndarray, w: int) -> np.ndarray:
    """ Compute the rolling median of the input array.

        Input:
            v [np.ndarray]: input array
            w [int]: size of the rolling window

        Output:
            ret [np.ndarray]: rolling mad output array of length len(v) - w + 1
    """

    md = np.nanmedian(rolling_window(v, w), axis=1)
    md = np.r_[[md[0]]*(w-1), md]
    dmean = np.abs(v - md)
    return np.nanmedian(rolling_window(dmean, w), axis=1)


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


def series_momenta(ts: np.ndarray, axis: int = 0) -> tuple:
    """ Calculates first 4 momenta of the input series.

        Input:
            ts [np.ndarray]: value series
            axis [int]: axis to calculate along (Default: 0)

        Output:
            mu [Union[float, np.ndarray]]: mean
            var [Union[float, np.ndarray]]: variance
            skewness [Union[float, np.ndarray]]: skewness (third momentum)
            kurtosis [Union[float, np.ndarray]]: kurtosis (fourth momentum)
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


def skewness(ts: np.ndarray, axis: int = 0) -> float:
    """ Calculates the skewness - third standard moment.

        Input:
            ts [np.ndarray]: value series
            axis [int]: axis to calculate along (Default: 0)

        Output:
            skew [Union[float, np.ndarray]]: skewness
    """
    ts_zm = ts - np.nanmean(ts, axis=axis)
    return np.power(ts_zm, 3) / (np.nanstd(ts, axis=axis) ** 3)
