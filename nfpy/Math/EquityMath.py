#
# Tools
#

import numpy as np
from typing import Union
from scipy import stats

from .DiscountFactor import dcf
from .TSUtils import (dropna, rolling_sum, rolling_window, trim_ts, last_valid_index)


def adj_factors(ts: np.ndarray, dt: np.ndarray, div: np.ndarray,
                div_dt: np.ndarray) -> np.ndarray:
    """ Calculate the adjustment factors given a dividend series.

        Input:
            ts [np.ndarray]: price series to calculate the yield
            dt [np.ndarray]: price series date index
            div [np.ndarray]: dividend series
            div_dt [np.ndarray]: dividend series date index

        Output:
            adjfc [np.ndarray]: series of adjustment factors
    """
    adj = np.ones(ts.shape)

    # Calculate conversion factors
    idx = np.searchsorted(dt, div_dt)
    for n, i in enumerate(idx):
        try:
            v = last_valid_index(ts, i)
            # if v != i:
            #     print("ts[{} - {}] = {} -->  ts[{} - {}] = {}"
            #           .format(i, dt[i], ts[i], v, dt[v], ts[v]))
        except ValueError:
            pass
        else:
            adj[i] -= div[n] / ts[v]
        # print("div[{}] = {}     ts[{}] = {}     adj = {}".format(n, div[n], i, v, adj[i]))

    cp = np.nancumprod(adj)
    return adj / cp * cp[-1]


def fv(cf: np.ndarray, r: Union[float, np.ndarray],
       t: np.ndarray = None, accrued: float = .0) -> float:
    """ Fair value from discounted cash flow that are calculated if not present.

        Input:
            cf [np.ndarray]: data (periods, value) of cash flows
            r [Union[float, np.ndarray]]: if float is the rate corresponding to the
                    yield to maturity. If ndarray calculate from the term structure
            t [np.ndarray]: array of tenors
            accrued [float]: accrued interest to subtract from dirty price

        Output:
            _r [float]: fair value
    """
    _dcf = dcf(cf, r, t)
    return float(_dcf.sum()) - accrued


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
    tsa, dts = trim_ts(ts, dt, start=start, end=end)
    prx, _ = trim_ts(proxy, dt, start=start, end=end)

    v, mask = dropna(np.vstack((tsa, prx)))

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


def capm_beta(dt: np.ndarray, ts: np.ndarray, idx: np.ndarray,
              start: np.datetime64 = None, end: np.datetime64 = None) -> tuple:
    """ Gives the beta of a series with respect to another (an index).

        Input:
            dt [np.ndarray]: dates series under analysis
            ts [np.ndarray]: return series under analysis
            idx [np.ndarray]: market proxy return time series
            start [np.datetime64]: start date of the series (default: None)
            end [np.datetime64]: end date of the series excluded (default: None)

        Output:
            beta [float]: the beta
    """
    # That end > start is NOT checked at this level
    tsa, _ = trim_ts(ts, dt, start=start, end=end)
    prx, _ = trim_ts(idx, dt, start=start, end=end)

    v, _ = dropna(np.vstack((tsa, prx)))

    prx_var = np.var(prx)
    covar = np.cov(v[0, :], v[1, :], bias=True)

    return covar[0, 1] / prx_var


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


def tev(dt: np.ndarray, r: np.ndarray, bkr: np.ndarray,
        start: np.datetime64 = None, end: np.datetime64 = None,
        w: int = None) -> tuple:
    """ Calculates the Tracking Error Volatility (TEV) between a series of
        returns and a benchmark one.

        Input:
            dt [np.ndarray]: dates series
            r [np.ndarray]: returns series
            bkr [np.ndarray]: benchmark return series
            start [pd.Timestamp]: start date of the series (default: None)
            end [pd.Timestamp]: end date of the series excluded (default: None)
            w [int]: rolling window size (default: None)

        Output:
            dt [np.ndarray]: TEV dates series
            tev [np.ndarray]: series of TEV
    """
    r, dts = trim_ts(r, dt, start=start, end=end)
    bkr, _ = trim_ts(bkr, dt, start=start, end=end)

    v, mask = dropna(np.vstack(r, bkr))

    if not w:
        res = np.std(r - bkr)
        dts = None
    else:
        res = np.std(rolling_window((r - bkr), w), axis=1)
        dts = dts[mask][w - 1:]

    return dts, res


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
    delta = (r - rt)
    return rt, delta
