#
# Risk_
# Low level functions for risk to Cythonize
#

import numpy as np
from scipy import stats
from typing import Optional

from .TSUtils_ import (dropna, fillna, rolling_sum,
                       rolling_window, search_trim_pos)
from nfpy.Tools import Exceptions as Ex


def beta(dt: np.ndarray, ts: np.ndarray, proxy: np.ndarray,
         start: Optional[np.datetime64] = None,
         end: Optional[np.datetime64] = None, w: Optional[int] = None) \
        -> tuple:
    """ Calculates the beta of a series with respect to a benchmark as the slope
        of the linear regression between the two.

        Input:
            dt [np.ndarray]: dates time series
            ts [np.ndarray]: equity or other series under analysis
            proxy [np.ndarray]: reference proxy time series
            start [np.datetime64]: start date of the series (Default: None)
            end [np.datetime64]: end date of the series excluded (Default: None)
            w [int]: window size if rolling (Default: None)

        Output:
            dt [Union[np.ndarray, TyDate]]: date (only if rolling else None)
            slope [Union[np.ndarray, float]]: the beta
            adj_beta [Union[np.ndarray, float]]: the adjusted beta
            intercept [Union[np.ndarray, float]]: intercept of the regression
    """
    if (dt.shape != ts.shape != proxy.shape) and len(dt.shape) > 1:
        raise Ex.ShapeError('The series must have the same length')

    slc = search_trim_pos(dt, start=start, end=end)
    v = np.vstack((ts[slc], proxy[slc]))
    dts = dt[slc]

    if not w:
        # scipy.linregress() is not robust against nans, therefore we clean them
        # and keep the dates series consistent.
        v, mask = dropna(v)
        dts = dts[-1:]
        slope, intercept, _, _, std_err = stats.linregress(v[1, :], v[0, :])

    else:
        sumx = rolling_sum(v[1, :], w)
        sumy = rolling_sum(v[0, :], w)
        sumxy = rolling_sum(v[1, :] * v[0, :], w)
        sumxx = rolling_sum(v[1, :] * v[1, :], w)

        slope = (w * sumxy - sumx * sumy) / (w * sumxx - sumx * sumx)
        intercept = (sumy - slope * sumx) / w
        dts = dts[w - 1:]

    adj_beta = 1. / 3. + 2. / 3. * slope

    return dts, slope, adj_beta, intercept


def capm_beta(dt: np.ndarray, ts: np.ndarray, idx: np.ndarray,
              start: Optional[np.datetime64] = None,
              end: Optional[np.datetime64] = None) -> float:
    """ Gives the beta of a series with respect to another (an index).

        Input:
            dt [np.ndarray]: dates series under analysis
            ts [np.ndarray]: return series under analysis
            idx [np.ndarray]: market proxy return time series
            start [np.datetime64]: start date of the series (Default: None)
            end [np.datetime64]: end date of the series excluded (Default: None)

        Output:
            beta [float]: the beta
    """
    if (dt.shape != ts.shape != idx.shape) and len(dt.shape) > 1:
        raise Ex.ShapeError('The series must have the same length')

    slc = search_trim_pos(dt, start=start, end=end)
    v = dropna(
        np.vstack((ts[slc], idx[slc]))
    )[0]

    prx_var = np.var(v[1, :])
    covar = np.cov(v[0, :], v[1, :], bias=True)

    return covar[0, 1] / prx_var


def drawdown(ts: np.ndarray, w: int) -> tuple[np.ndarray, np.ndarray]:
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
    mdd[w - 1:] = np.nanmax(rolling_window(dd, w), axis=1)
    return dd, mdd


def sharpe(dt: np.ndarray, xc: np.ndarray, br: Optional[np.ndarray] = None,
           start: Optional[np.datetime64] = None,
           end: Optional[np.datetime64] = None) -> float:
    """ Calculates the Sharpe ratio for the given return series. If the return
        series contains returns instead of excess returns, the base rate series
        must also be given to compute excess returns.

        Input:
            xc [np.ndarray]: series of excess returns wrt a base return series
            br [np.ndarray]: base rate series. Subtracted to xc to obtain excess
                             returns (Default: None)
            start [np.datetime64]: start date of the series (Default: None)
            end [np.datetime64]: end date of the series excluded (Default: None)

        Output:
            sharpe [float]: Sharpe ratio
    """
    if (dt.shape != xc.shape != br.shape) and len(dt.shape) > 1:
        raise Ex.ShapeError('The series must have the same length')

    slc = search_trim_pos(dt, start=start, end=end)
    v = xc[slc]

    # If a base rate is provided we obtain excess returns
    if br is not None:
        v = v - br[slc]

    return np.nanmean(v) / np.nanstd(v)


def sml(r: float, exposure: float, rf: float, rm: float) -> tuple[float, float]:
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


def te(dt: np.ndarray, r: np.ndarray, bkr: np.ndarray,
       start: Optional[np.datetime64] = None,
       end: Optional[np.datetime64] = None, w: Optional[int] = None) \
        -> tuple[np.ndarray, np.ndarray]:
    """ Calculates the Tracking Error (TE) between a the returns of an asset and
        its benchmark.

        Input:
            dt [np.ndarray]: dates series
            r [np.ndarray]: returns series
            bkr [np.ndarray]: benchmark return series
            start [np.datetime64]: start date of the series (Default: None)
            end [np.datetime64]: end date of the series excluded (Default: None)
            w [int]: rolling window size (Default: None)

        Output:
            dt [np.ndarray]: TEV dates series
            tev [np.ndarray]: series of TEV
    """
    if (dt.shape != r.shape != bkr.shape) and len(dt.shape) > 1:
        raise Ex.ShapeError('The series must have the same length')

    slc = search_trim_pos(dt, start=start, end=end)
    dts = dt[slc]

    if not w:
        res = np.sqrt(
            np.nanstd(r[slc] - bkr[slc])
        )
    else:
        res = np.sqrt(
            np.nanstd(
                rolling_window((r[slc] - bkr[slc]), w),
                axis=1
            )
        )
        dts = dts[w - 1:]

    return dts, res
