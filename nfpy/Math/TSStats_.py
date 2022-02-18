#
# TSStats_
# Low level functions for time series to Cythonize
#

import numpy as np
from typing import Optional

from nfpy.Tools import Exceptions as Ex

from .TSUtils_ import (dropna, search_trim_pos)


def correlation(dt: np.ndarray, ts: np.ndarray, bmk: np.ndarray,
                start: Optional[np.datetime64] = None,
                end: Optional[np.datetime64] = None) -> np.ndarray:
    """ Calculates the correlation between a series and a benchmark.

        Input:
            dt [np.ndarray]: dates time series
            ts [np.ndarray]: equity or other series under analysis
            bmk [np.ndarray]: reference benchmark time series
            start [np.datetime64]: start date of the series (default: None)
            end [np.datetime64]: end date of the series excluded (default: None)

        Output:
            corr [np.ndarray]: matrix of correlation coefficients
    """
    if (dt.shape != ts.shape != bmk.shape) and len(dt.shape) > 1:
        raise Ex.ShapeError('The series must have the same length')

    slc = search_trim_pos(dt, start=start, end=end)
    return np.corrcoef(
        dropna(
            np.vstack((ts[slc], bmk[slc])),
            axis=0
        )[0]
    )


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


def skewness(ts: np.ndarray, axis: int = 0) -> float:
    """ Calculates the third standard moment. """
    ts_zm = ts - np.nanmean(ts, axis=axis)
    return np.power(ts_zm, 3) / (np.nanstd(ts, axis=axis) ** 3)
