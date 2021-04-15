#
# Yields and Returns functions
# Functions to deal with yields and returns
#

from typing import Union

import numpy as np
import pandas as pd

from .TSUtils import trim_ts


def ret(v: pd.Series, fillna: str = 'pad', w: int = 1) -> pd.Series:
    """ Compute returns for the series using the pandas function pct_change()

        Inputs:
            df [pd.Series]: input DataFrame
            w [int]: window length (default 1)
            fillna [str]: method to deal with missing data (default 'pad')

        Output:
            _r [pd.Series]: indexed series of simple returns
    """
    return v.pct_change(w, fill_method=fillna)


def logret(v: pd.Series, fillna: str = 'pad', w: int = 1) -> pd.Series:
    """ Compute is_log returns from the series of simple returns or prices

        Inputs:
            df [pd.Series]: input DataFrame
            w [int]: window length, used only for prices (default 1)
            fillna [str]: method to deal with missing data, used only for
                    prices (default 'pad')

        Output:
            _r [pd.Series]: indexed series of is_log returns
    """
    v = ret(v, fillna, w)
    return v.add(1.).log()


def tot_ret(ts: np.ndarray, dt: np.ndarray = None, start: np.datetime64 = None,
            end: np.datetime64 = None, is_log: bool = False) -> float:
    """ Calculates the total return from a series by compounding the returns.
        Useful to save memory if only the last value is needed.

        Input:
            ts [np.ndarray]: return series
            dt [np.ndarray]: date series (default: None)
            start [np.datetime64]: start date of the series (default: None)
            end [np.datetime64]: end date of the series excluded (default: None)
            is_log [bool]: set True for logarithmic returns (default: False)

        Output:
            ret [float]: expected return
    """
    if dt is not None:
        ts, _ = trim_ts(ts, dt, start=start, end=end)

    if is_log:
        r = np.nansum(ts, axis=0)
    else:
        r = np.nanprod((1. + ts), axis=0) - 1.

    return r


def comp_ret(ts: np.ndarray, dt: np.ndarray = None, start: np.datetime64 = None,
             end: np.datetime64 = None, base: float = 1., is_log: bool = False
             ) -> tuple:
    """ Calculates the series of total returns by compounding. Identical to
        tot_ret() but returns the compounded series instead of the last value
        only.

        Input:
            ts [np.ndarray]: return series
            dt [np.ndarray]: date series (default: None)
            start [np.datetime64]: start date of the series (default: None)
            end [np.datetime64]: end date of the series excluded (default: None)
            base [float]: base level (default: 1.)
            is_log [bool]: set True for logarithmic returns (default: False)

        Output:
            res [np.ndarray]: compounded returns series
            dt [np.ndarray]: trimmed dates series
    """
    if dt is not None:
        ts, dt = trim_ts(ts, dt, start=start, end=end)

    if is_log:
        res = base * np.exp(np.nancumsum(ts, axis=0))
    else:
        res = base * np.nancumprod((1. + ts), axis=0)

    return res, dt


def e_ret(ts: np.ndarray, dt: np.ndarray = None, start: np.datetime64 = None,
          end: np.datetime64 = None, is_log: bool = False) -> float:
    """ Expected return for the series in input. It corresponds to the geometric
        mean for standard returns, and to the simple mean for log returns.

        Input:
            ts [np.ndarray]: values of the series under analysis
            dt [np.ndarray]: dates of the series under analysis (default: None)
            start [np.datetime64]: start date of the series (default: None)
            end [np.datetime64]: end date of the series excluded (default: None)
            is_log [bool]: set True for logarithmic returns (default: False)

        Output:
            exp_ret [float]: expected value of the return
    """
    if dt is not None:
        ts, _ = trim_ts(ts, dt, start=start, end=end)

    if is_log:
        exp_r = np.nanmean(ts, axis=0)
    else:
        exp_r = compound(tot_ret(ts, dt), 1. / ts.shape[0])

    return exp_r


def compound(r: Union[float, np.ndarray], t: Union[int, np.ndarray],
             n: int = 1) -> Union[float, np.ndarray]:
    """ Compound input rate of return.

        Input:
            r [Union[float, np.ndarray]]: rate of return
            t [Union[int, np.ndarray]]: time of compounding
            n [int]: frequency of compounding
    """
    return (1. + r / n) ** t - 1.
