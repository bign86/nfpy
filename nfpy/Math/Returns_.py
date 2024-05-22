#
# Yields and Returns
# Functions to deal with yields and returns
#

import cmath
import numpy as np
from typing import Union

import nfpy.IO.Utilities as Ut

from .TSUtils_ import (last_valid_value, next_valid_value)


def compound(r: Union[float, np.ndarray], t: Union[int, float, np.ndarray],
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
    """ Calculates the series of total cumulated returns.

        Input:
            ts [np.ndarray]: returns series
            is_log [bool]: set True for logarithmic returns (Default: False)

        Output:
            res [np.ndarray]: compounded returns series
    """
    Ut.print_deprecation('Math.comp_ret() -> cutils.compound_ret_from_ret() or cutils.compound_ret_from_ret_nans()')
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
    Ut.print_deprecation("Math.e_ret() -> DON'T USE")
    return np.nanmean(ts, axis=0)[0]


def tot_ret(v: np.ndarray, is_log: bool = False) -> float:
    """ Computes the total return over the given period from a price series.

        Inputs:
            v [np.ndarray]: price series
            is_log [bool]: set True for logarithmic returns (Default: False)

        Output:
            _r [np.ndarray]: return over the period
    """
    Ut.print_deprecation('Math.tot_ret() -> cutils.total_ret_from_p_nans()')
    fp = next_valid_value(v)[0]
    lp = last_valid_value(v)[0]
    if is_log:
        res = cmath.log(lp / fp)
    else:
        res = (lp / fp) - 1.

    return res
