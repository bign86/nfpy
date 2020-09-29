#
# Yields and Returns functions
# Functions to deal with yields and returns
#

from typing import Union

import numpy as np
import pandas as pd

from nfpy.Tools.TSUtils import trim_ts


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
    return np.log(v + 1.)


def tot_ret(ts: np.array, dt: np.array, start: pd.Timestamp = None,
            end: pd.Timestamp = None, is_log: bool = False) -> float:
    """ Calculates the total return from a series.

        Input:
            ts [np.array]: return series
            dt [np.array]: date series
            start [pd.Timestamp]: start date of the series (default: None)
            end [pd.Timestamp]: end date of the series excluded (default: None)
            is_log [bool]: set True for logarithmic returns (default: False)

        Output:
            ret [float]: expected return
    """
    v, _ = trim_ts(ts, dt, start=start, end=end)

    if is_log:
        r = np.nansum(v, axis=0)
    else:
        r = np.nanprod((1. + v), axis=0) - 1.

    return r


def expct_ret(ts: np.array, dt: np.array, start: pd.Timestamp = None,
              end: pd.Timestamp = None, is_log: bool = False) -> float:
    """ Expected return for the series in input. It corresponds to the geometric
        mean for standard returns, and to the simple mean for log returns.

        Input:
            ts [np.array]: values of the series under analysis
            dt [np.array]: dates of the series under analysis
            start [pd.Timestamp]: start date of the series (default: None)
            end [pd.Timestamp]: end date of the series excluded (default: None)
            is_log [bool]: set True for logarithmic returns (default: False)

        Output:
            slope [float]: the beta
            intercpt [float]: intercept of the regression
            std_err [float]: regression error
    """
    v, t = trim_ts(ts, dt, start=start, end=end)

    if is_log:
        expv = np.nanmean(v, axis=0)
    else:
        expv = compound(tot_ret(v, t), 1./v.shape[0])

    return expv


def compound(r: Union[float, np.array], t: Union[int, np.array], n: int = 1) \
        -> Union[float, np.array]:
    """ Compound input rate of return.

        Input:
            r [Union[float, np.array]]: rate of return
            t [Union[int, np.array]]: time of compounding
            n [int]: frequency of compounding
    """
    return (1. + r / n) ** t - 1.
