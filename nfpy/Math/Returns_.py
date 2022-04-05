#
# Yields and Returns functions
# Functions to deal with yields and returns
#

import cmath
from typing import Union

import numpy as np

from .TSUtils_ import (ffill_cols, last_valid_value, next_valid_value)


def compound(r: Union[float, np.ndarray], t: Union[int, np.ndarray],
             n: int = 1) -> Union[float, np.ndarray]:
    """ Compound input rate of return.

        Input:
            r [Union[float, np.ndarray]]: rate of return over some period
            t [Union[int, np.ndarray]]: compounding periods
            n [int]: frequency of compounding relative to the period of <r>
    """
    return (1. + r / n) ** t - 1.


def comp_ret(ts: np.ndarray, is_log: bool = False) \
        -> np.ndarray:
    """ Calculates the series of total cumulated returns. Identical to
        cumulate_ret() but returns the compounded series instead of the last
        value only.

        Input:
            ts [np.ndarray]: returns series
            is_log [bool]: set True for logarithmic returns (Default: False)

        Output:
            res [np.ndarray]: compounded returns series
    """
    if is_log:
        res = np.exp(np.nancumsum(ts, axis=0))
    else:
        res = np.nancumprod((1. + ts), axis=0)

    return res


def cumulate_ret(ts: np.ndarray, is_log: bool = False) -> float:
    """ Calculates the total cumulated return from a series of returns.
        Identical to comp_ret() but returns the last compounded return instead
        of the whole series.

        Input:
            ts [np.ndarray]: returns series
            is_log [bool]: set True for logarithmic returns (Default: False)

        Output:
            ret [float]: expected return
    """
    if is_log:
        r = np.nansum(ts, axis=0)
    else:
        r = np.nanprod((1. + ts), axis=0) - 1.

    return r


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
        exp_r = compound(cumulate_ret(ts), 1. / ts.shape[0])

    return exp_r


def logret(v: np.ndarray) -> np.ndarray:
    """ Computes is_log returns from the series of simple returns or prices

        Inputs:
            v [np.ndarray]: input series

        Output:
            _r [np.ndarray]: indexed series of log returns
    """
    vf = ffill_cols(v)
    return np.log(vf[1:] / vf[:-1])


def ret(v: np.ndarray) -> np.ndarray:
    """ Computes returns for the series using the pandas function pct_change()

        Inputs:
            v [np.ndarray]: input series

        Output:
            _r [np.ndarray]: indexed series of simple returns
    """
    vf = ffill_cols(v)
    return vf[1:] / vf[:-1] - 1.


def tot_ret(v: np.ndarray, is_log: bool = False) -> float:
    """ Computes the total return over the given period from a price series.

        Inputs:
            v [np.ndarray]: price series
            is_log [bool]: set True for logarithmic returns (Default: False)

        Output:
            _r [np.ndarray]: return over the period
    """
    fp = next_valid_value(v)[0]
    lp = last_valid_value(v)[0]
    if is_log:
        res = cmath.log(lp / fp)
    else:
        res = (lp / fp) - 1.

    return res
