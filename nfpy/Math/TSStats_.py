#
# TS
# Low level functions for time series to Cythonize
#

import numpy as np
from scipy import stats

from .TSUtils_ import (dropna, fillna, rolling_sum,
                       rolling_window, trim_ts)


def beta(dt: np.ndarray, ts: np.ndarray, proxy: np.ndarray,
         start: np.datetime64 = None, end: np.datetime64 = None,
         w: int = None) -> tuple:
    """ Gives the beta of a series with respect to another (an index).

        Input:
            dt [np.ndarray]: dates time series
            ts [np.ndarray]: equity or other series under analysis
            proxy [np.ndarray]: reference proxy time series
            start [np.datetime64]: start date of the series (default: None)
            end [np.datetime64]: end date of the series excluded (default: None)
            w [int]: window size if rolling (default: None)

        Output:
            dt [Union[np.ndarray, None]]: date (only if rolling else None)
            slope [Union[np.ndarray, float]]: the beta
            adj_beta [Union[np.ndarray, float]]: the adjusted beta
            intercept [Union[np.ndarray, float]]: intercept of the regression
    """
    # That end > start is NOT checked at this level
    # TODO: substitute with a pure view
    tsa, dts = trim_ts(ts, dt, start=start, end=end)
    prx, _ = trim_ts(proxy, dt, start=start, end=end)

    v, mask = dropna(np.vstack((tsa, prx)))
    mask = mask.flatten()

    if not w:
        slope, intercept, _, _, std_err = stats.linregress(v[1, :], v[0, :])
        adj_beta = 1. / 3. + 2. / 3. * slope
        dts = None

    else:
        sumx = rolling_sum(v[1, :], w)
        sumy = rolling_sum(v[0, :], w)
        sumxy = rolling_sum(v[1, :] * v[0, :], w)
        sumxx = rolling_sum(v[1, :] * v[1, :], w)

        slope = (w * sumxy - sumx * sumy) / (w * sumxx - sumx * sumx)
        intercept = (sumy - slope * sumx) / w

        slope, _ = dropna(slope)
        adj_beta = 1. / 3. + 2. / 3. * slope
        intercept, _ = dropna(intercept)
        dts = dts[mask][w - 1:]

    return dts, slope, adj_beta, intercept


def correlation(dt: np.ndarray, ts: np.ndarray, proxy: np.ndarray,
                start: np.datetime64 = None, end: np.datetime64 = None,
                w: int = None) -> tuple:
    """ Gives the beta of a series with respect to another (an index).

        Input:
            dt [np.ndarray]: dates time series
            ts [np.ndarray]: equity or other series under analysis
            proxy [np.ndarray]: reference proxy time series
            start [np.datetime64]: start date of the series (default: None)
            end [np.datetime64]: end date of the series excluded (default: None)
            w [int]: window size if rolling (default: None)

        Output:
            dt [Union[np.ndarray, None]]: date (only if rolling else None)
            slope [Union[np.ndarray, float]]: the beta
            intercept [Union[np.ndarray, float]]: intercept of the regression
            std_err [Union[np.ndarray, float]]: regression error
    """
    # That end > start is NOT checked at this level
    # TODO: substitute with a pure view
    tsa, dts = trim_ts(ts, dt, start=start, end=end)
    prx, _ = trim_ts(proxy, dt, start=start, end=end)

    v, mask = dropna(np.vstack((tsa, prx)))

    if not w:
        corr = np.corrcoef(v[1, :], v[0, :])
        dts = None

    else:
        # TODO: to be implemented
        corr = None

    return dts, corr


def drawdown(ts: np.ndarray, w: int) -> tuple:
    """ Calculate the maximum drawdown in the given time window.

        Input:
            ts [np.ndarray]: time series
            w [int]: window size

        Output:
            dd [np.ndarray]: drawdown
            mdd [np.ndarray]: max drowdown in the window
    """
    w = abs(int(w))
    idx_max = np.nanargmax(
        rolling_window(ts, w),
        axis=1
    )
    idx_max += np.arange(len(idx_max))
    dd = np.take(ts, idx_max) / ts[w - 1:] - 1.
    mdd = np.empty_like(dd)
    mdd[:w] = np.maximum.accumulate(fillna(dd[:w], -1., inplace=True))
    mdd[w-1:] = np.nanmax(rolling_window(dd, w), axis=1)
    return dd, mdd


def sharpe(dt: np.ndarray, xc: np.ndarray, br: np.ndarray = None,
           start: np.datetime64 = None, end: np.datetime64 = None,
           w: int = None) -> tuple:
    """ Calculates the Sharpe ratio for the given return series.

        Input:
            xc [np.ndarray]: series of excess returns wrt a base return series
            br [np.ndarray]: base rate series. Subtracted to xc to obtain excess
                             returns (default: None)
            start [np.datetime64]: start date of the series (default: None)
            end [np.datetime64]: end date of the series excluded (default: None)
            w [int]: rolling window size (default: None)

        Output:
            sharpe [pd.Series]: Sharpe ratio series
    """
    xc, dts = trim_ts(xc, dt, start=start, end=end)

    # If a base rate is provided we obtain excess returns
    if br:
        br, _ = trim_ts(br, dt, start=start, end=end)
        xc = xc - br

    xc, mask = dropna(xc)

    if not w:
        exp_ret = np.mean(xc)
        exp_std = np.std(xc)
        dts = None
    else:
        exp_ret = np.mean(rolling_window(xc, w), axis=1)
        exp_std = np.std(rolling_window(xc, w), axis=1)
        dts = dts[mask][w - 1:]

    return dts, exp_ret / exp_std


def sml(r: float, exposure: float, rf: float, rm: float) -> tuple:
    """ Calculate the theoretical fair return of the asset according to the SML
        line and the actual asset relative over-/under- pricing.

        Input:
            r [float]: return of the asset
            exposure [float]: beta of the asset
            rf [float]: risk free return
            rm [float]: return of the market

        Output:
            rt [float]: theoretical SML fair return
            delta [float]: over-/under- pricing
    """
    rt = (rm - rf) * exposure + rf
    return rt, (r - rt)


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
