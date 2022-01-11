#
# Equity Math
# Mathematical functions for equities
#

import numpy as np
from typing import Union

from .DiscountFactor import dcf
from .TSUtils_ import (dropna, rolling_window, trim_ts)


def fv(cf: np.ndarray, r: Union[float, np.ndarray],
       t: np.ndarray = None, accrued: float = .0) -> float:
    """ Fair value from discounted cash flow that are calculated if not present.

        Input:
            cf [np.ndarray]: data (periods, value) of cash flows
            r [Union[float, np.ndarray]]: if float is the rate corresponding to
                the yield to maturity. If ndarray calculate from the term structure
            t [np.ndarray]: array of tenors
            accrued [float]: accrued interest to subtract from dirty price

        Output:
            _r [float]: fair value
    """
    _dcf = float(dcf(cf, r, t).sum())
    return _dcf - accrued


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
