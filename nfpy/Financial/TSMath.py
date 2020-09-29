#
# Tools
#

# import warnings
from typing import Iterable, Tuple, Union
import numpy as np
import pandas as pd
from scipy import stats

from nfpy.Financial.DiscountFactor import dcf
from nfpy.Handlers.Calendar import get_calendar_glob
from nfpy.Tools.TSUtils import trim_ts, rolling_sum, dropna

# from nfpy.Financial.Returns import compound, tot_ret
# from nfpy.Tools.TSUtils import trim_ts


# def expct_value(v: pd.Series, start: pd.Timestamp = None,
#                 end: pd.Timestamp = None, is_log: bool = False)\
#         -> Union[float, pd.Series]:
#     """ Expected value for the series in input.
#
#         Input:
#             v [pd.Series]: series under analysis
#             start [pd.Timestamp]: start date of the series (default: None)
#             end [pd.Timestamp]: end date of the series excluded (default: None)
#             is_log [bool]: set True for logarithmic returns (default: False)
#
#         Output:
#             slope [float]: the beta
#             intercpt [float]: intercept of the regression
#             std_err [float]: regression error
#     """
#     # That end > start is NOT checked at this level
#     if start or end:
#         v = trim_ts(v, start, end)
#     # if start:
#     #     v = v.loc[start:]
#     # if end:
#     #     v = v.loc[:end]
#
#     if is_log:
#         expv = v.mean()
#     else:
#         n = len(v)
#         expv = compound(tot_ret(v), n)
#     return expv


def adjust_series(ts: pd.Series, adjts_list: Iterable[pd.Series] = None,
                  fcts_list: Iterable[pd.Series] = None) -> Tuple[pd.Series, pd.Series]:
    """ Creates an adjusted series by applying a series of adjusting factors.
    
        Input:
            ts [pd.Series]: series to be adjusted
            adjts_list [Sequence[ps.Series]]: sequence of adjusting series already
                in the form of conversion factors
            fcts_list: Sequence[ps.Series]: sequence of adjusting series yet to be
                transformed in conversion factors. It is converted calculating the
                return over the non-adjusted series (i.e.: a series of monetary
                dividends is converted dividing by the equity price series)
        
        Output:
            adjts [pd.Series]: adjusted series
            adjfc [pd.Series]: adjusting factors used
    """
    # Create a series of adjusting factors
    cal = get_calendar_glob().calendar
    adjfc = pd.Series(1., index=cal)

    # If both none, quick exit, with factors all equal to 1
    if not adjts_list and not fcts_list:
        return ts, adjfc

    # Calculate new conversion factors
    if fcts_list:
        for fcts in fcts_list:
            fc = 1. - (fcts / ts)
            fc = fc.fillna(1.)
            cp = fc.cumprod()
            adjfc = adjfc * fc / cp * cp.iloc[-1]

    # Apply ready conversion factors
    if adjts_list:
        for adjts in adjts_list:
            fc = adjts.fillna(method='backfill', axis='index').fillna(1.)
            adjfc = adjfc * fc

    ts = ts * adjfc
    return ts, adjfc


def fv(cf: np.ndarray, r: Union[float, np.ndarray],
       t: np.ndarray = None, accrued: float = .0) -> float:
    """ Fair value from discounted cash flow that are calculated if not present.

        Input:
            cf [np.ndarray]: data (periods, value) of cash flows
            r Union[float, np.ndarray]: if float is the rate corresponding to the
                    yield to maturity. If ndarray calculate from the term structure
            t [np.ndarray]: array of tenors
            accrued [float]: accrued interest to subtract from dirty price

        Output:
            _r [float]: fair value
    """
    _dcf = dcf(cf, r, t)
    return float(_dcf.sum()) - accrued


def beta(equity: pd.Series, index: pd.Series, start: pd.Timestamp = None,
         end: pd.Timestamp = None, w: int = None) -> tuple:
    """ Gives the beta of a series with respect to another (an index).

        Input:
            equity [pd.Series]: equity or other series under analysis
            index [pd.Series]: reference proxy time series
            start [pd.Timestamp]: start date of the series (default: None)
            end [pd.Timestamp]: end date of the series excluded (default: None)
            w [int]: window size if rolling (default: None)

        Output:
            slope [float]: the beta
            intercpt [float]: intercept of the regression
            std_err [float]: regression error
    """
    # That end > start is NOT checked at this level
    equity = equity.loc[start:end]
    index = index.loc[start:end]

    df = pd.concat((equity, index), axis=1)
    df.dropna(inplace=True)
    df.columns = ['eq', 'idx_list']

    if not w:
        slope, intercpt, _, _, std_err = stats.linregress(df['idx_list'], df['eq'])

    else:
        sumx = df['idx_list'].rolling(w, min_periods=w).sum()
        sumy = df['eq'].rolling(w, min_periods=w).sum()
        sumxy = (df['idx_list'] * df['eq']).rolling(w, min_periods=w).sum()
        sumxx = (df['idx_list'] * df['idx_list']).rolling(w, min_periods=w).sum()

        slope = (w * sumxy - sumx * sumy) / (w * sumxx - sumx * sumx)
        intercpt = (sumy - slope * sumx) / w
        std_err = None

        slope.dropna(inplace=True)
        intercpt.dropna(inplace=True)

    return slope, intercpt, std_err


def beta_2(ts: np.ndarray, dt: np.ndarray, index: np.ndarray,
           start: pd.Timestamp = None, end: pd.Timestamp = None,
           w: int = None) -> tuple:
    """ Gives the beta of a series with respect to another (an index).

        Input:
            ts [np.ndarray]: equity or other series under analysis
            dt [np.ndarray]: dates time series
            index [np.ndarray]: reference proxy time series
            start [pd.Timestamp]: start date of the series (default: None)
            end [pd.Timestamp]: end date of the series excluded (default: None)
            w [int]: window size if rolling (default: None)

        Output:
            slope [float]: the beta
            intercpt [float]: intercept of the regression
            std_err [float]: regression error
    """
    # That end > start is NOT checked at this level
    tsa, _ = trim_ts(ts, dt, start=start, end=end)
    mkt, _ = trim_ts(ts, dt, start=start, end=end)

    v = np.vstack((dt, tsa, mkt))
    v = v[~np.isnan(v).any(axis=1)]

    if not w:
        slope, intercpt, _, _, std_err = stats.linregress(v[:, 2], v[:, 1])

    else:
        sumx = rolling_sum(mkt, w)
        sumy = rolling_sum(tsa, w)
        sumxx = rolling_sum(mkt*tsa, w)
        sumxy = rolling_sum(mkt*mkt, w)

        slope = (w * sumxy - sumx * sumy) / (w * sumxx - sumx * sumx)
        intercpt = (sumy - slope * sumx) / w
        std_err = None

        slope, _ = dropna(slope)
        intercpt, _ = dropna(intercpt)

    return dt[w - 1:], slope, intercpt, std_err


def capm(equity: pd.Series, index: pd.Series, start: pd.Timestamp = None,
         end: pd.Timestamp = None, w: int = None) -> tuple:
    """ Gives the beta of a series with respect to another (an index).

        Input:
            equity [pd.Series]: equity or other series under analysis
            index [pd.Series]: market proxy time series
            start [pd.Timestamp]: start date of the series (default: None)
            end [pd.Timestamp]: end date of the series excluded (default: None)
            w [int]: window size if rolling (default: None)

        Output:
            slope [float]: the beta
            intercpt [float]: intercept of the regression
            std_err [float]: regression error
    """
    # That end > start is NOT checked at this level
    equity = equity.loc[start:end]
    index = index.loc[start:end]

    df = pd.concat((equity, index), axis=1)
    df.dropna(inplace=True)
    df.columns = ['eq', 'idx_list']

    if not w:
        slope, intercpt, _, _, std_err = stats.linregress(df['idx_list'], df['eq'])

    else:
        sumx = df['idx_list'].rolling(w, min_periods=w).sum()
        sumy = df['eq'].rolling(w, min_periods=w).sum()
        sumxy = (df['idx_list'] * df['eq']).rolling(w, min_periods=w).sum()
        sumxx = (df['idx_list'] * df['idx_list']).rolling(w, min_periods=w).sum()

        slope = (w * sumxy - sumx * sumy) / (w * sumxx - sumx * sumx)
        intercpt = (sumy - slope * sumx) / w
        std_err = None

        slope.dropna(inplace=True)
        intercpt.dropna(inplace=True)

    return slope, intercpt, std_err


def sharpe(xc: pd.Series, br: pd.Series = None, w: int = None) -> pd.Series:
    """ Calculates the Sharpe ratio for the given return series.

        Input:
            xc [pd.Series]: series of excess returns wrt a base return series
            br [pd.Series]: base rate series. Subtracted to xc to obtain excess
                            returns (default: None)
            w [int]: rolling window size (default: None)

        Output:
            sharpe [pd.Series]: Sharpe ratio series
    """
    # If a base rate is provided we obtain excess returns
    if br:
        xc = xc - br

    if not w:
        exp_ret = xc.mean()
        exp_std = xc.std()
    else:
        exp_ret = xc.rolling(w, min_periods=1).mean()
        exp_std = xc.rolling(w, min_periods=1).std()
    return exp_ret / exp_std


def tev(r: pd.Series, bkr: pd.Series, w: int = None) -> pd.Series:
    """ Calculates the Tracking Error Volatility (TEV) between a series of
        returns and a benchmark one.

        Input:
            r [pd.Series]: return series
            bkr [pd.Series]: benckmark return series
            w [int]: rolling window size (default: None)

        Output:
            tev [pd.Series]: series of TEV
    """
    def _std(_r, _bkr):
        return np.sqrt(((_r - _bkr.mean())**2).mean())

    if not w:
        # res = (r - bkr).std()
        res = _std(r, bkr)
    else:
        # FIXME: !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #        should be sqrt(mean(r - mean(bkr))^2)
        #        not       sqrt(mean((r - bkr) - mean(r - bkr))^2)
        res = (r - bkr).rolling(w, min_periods=1).std()
    return res
