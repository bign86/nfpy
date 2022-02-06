#
# Yields and Returns functions
# Functions to deal with yields and returns
#

from typing import Union

import numpy as np

from .TSUtils_ import ffill_cols


def logret(v: np.ndarray) -> np.ndarray:
    """ Compute is_log returns from the series of simple returns or prices

        Inputs:
            v [np.ndarray]: input series

        Output:
            _r [np.ndarray]: indexed series of log returns
    """
    vf = ffill_cols(v)
    return np.log(vf[1:] / vf[:-1])


def ret(v: np.ndarray) -> np.ndarray:
    """ Compute returns for the series using the pandas function pct_change()

        Inputs:
            v [np.ndarray]: input series

        Output:
            _r [np.ndarray]: indexed series of simple returns
    """
    vf = ffill_cols(v)
    return vf[1:] / vf[:-1] - 1.


def tot_ret(ts: np.ndarray, is_log: bool = False) -> float:
    """ Calculates the total return from a series by compounding the returns.

        Input:
            ts [np.ndarray]: return series
            is_log [bool]: set True for logarithmic returns (default: False)

        Output:
            ret [float]: expected return
    """
    if is_log:
        r = np.nansum(ts, axis=0)
    else:
        r = np.nanprod((1. + ts), axis=0) - 1.

    return r


def comp_ret(ts: np.ndarray, is_log: bool = False) \
        -> np.ndarray:
    """ Calculates the series of total returns by compounding. Identical to
        tot_ret() but returns the compounded series instead of the last value
        only.

        Input:
            ts [np.ndarray]: return series
            is_log [bool]: set True for logarithmic returns (default: False)

        Output:
            res [np.ndarray]: compounded returns series
            dt [np.ndarray]: trimmed dates series
    """
    if is_log:
        res = np.exp(np.nancumsum(ts, axis=0))
    else:
        res = np.nancumprod((1. + ts), axis=0)

    return res


def e_ret(ts: np.ndarray, is_log: bool = False) -> float:
    """ Expected return for the series in input. It corresponds to the geometric
        mean for standard returns, and to the simple mean for log returns.

        Input:
            ts [np.ndarray]: values of the series under analysis
            is_log [bool]: set True for logarithmic returns (Default: False)

        Output:
            exp_ret [float]: expected value of the return
    """
    if is_log:
        exp_r = np.nanmean(ts, axis=0)
    else:
        exp_r = compound(tot_ret(ts), 1. / ts.shape[0])

    return exp_r


def compound(r: Union[float, np.ndarray], t: Union[int, np.ndarray],
             n: int = 1) -> Union[float, np.ndarray]:
    """ Compound input rate of return.

        Input:
            r [Union[float, np.ndarray]]: rate of return over some period
            t [Union[int, np.ndarray]]: compounding periods
            n [int]: frequency of compounding relative to the period of <r>
    """
    return (1. + r / n) ** t - 1.
