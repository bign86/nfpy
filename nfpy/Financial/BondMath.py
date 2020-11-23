#
# Bond math functions
# Functions with bond math
#

from typing import Union
import numpy as np
# import pandas as pd
from scipy.optimize import newton

from nfpy.Financial.DiscountFactor import dcf
from nfpy.Financial.EquityMath import fv
from nfpy.Handlers.DatatypeFactory import get_dt_glob
from nfpy.Tools.Constants import DAYS_IN_1Y
from nfpy.Tools.Exceptions import IsNoneError
from nfpy.Tools.TSUtils import trim_ts


def ytm(cf: np.ndarray, p0: float, acc: float = .0) -> float:
    """ Calculated the YTM using the values from the cash flow dataframe as
        a numpy array for speed and reliability.
    """

    def _min_ytm(r, dt):
        return fv(dt, r, None, acc) - p0

    return newton(_min_ytm, .02, args=(cf,))


def __time_cf(cf: np.ndarray, p0: float, acc: float, exp: float) -> float:
    _ytm = ytm(cf, p0, acc)
    wflow = dcf(cf, _ytm) * (cf[0, :] ** exp)
    return float(wflow.sum()) / p0


def duration(cf: np.ndarray, p0: float, acc: float = .0) -> float:
    """ Bond duration.

        Input:
            cf [np.ndarray]: data (periods, value) of cash flows
            p0 [float]: market price at t0
            accrued [float]: accrued interest to subtract from dirty price

        Output:
            _r [float]: duration
    """
    return __time_cf(cf, p0, acc, 1.)


def convexity(cf: np.ndarray, p0: float, acc: float = .0) -> float:
    """ Bond convexity.

        Input:
            cf [np.ndarray]: dataframe (periods, value) of cash flows
            p0 [float]: market price at t0
            accrued [float]: accrued interest to subtract from dirty price

        Output:
            _r [float]: duration
    """
    return __time_cf(cf, p0, acc, 2.)


def accrued(dt: np.ndarray, t0: np.datetime64, inception: np.datetime64) -> tuple:
    """ Calculate accrued interest. In input must be supplied the series of
        dates and the reference date.

        Input:
            dt [np.ndarray]: series of dates
            t0 [np.datetime64]: reference date, must be given if dt is supplied
            inception [np.datetime64]: inception date

        Output:
            perc [float]: percentage of cash flow accrued
            idx [int]: index of the cash flow where the accrued is assigned
    """
    td = np.timedelta64(DAYS_IN_1Y, 'D')
    # t0 = np.datetime64(t0, dtype='datetime64[ns]')

    # Find the relevant cash flows
    pe = (dt - t0) / td
    t0_idx = np.where(np.diff(np.sign(pe) > 0))[0]

    # If there is no index found we accrue since inception
    if len(t0_idx) == 0:
        # idx, t_old = 0, np.datetime64(inception, dtype='datetime64[ns]')
        idx, t_old = 0, inception

    # If there is an index we accrue since the date found
    else:
        idx = int(t0_idx) + 1
        t_old = dt[idx - 1]

    perc = pe[idx] * td / (dt[idx] - t_old)
    perc = .0 if perc == 1. else perc
    return perc, idx, pe


def cash_flows(cf: np.ndarray, dt: np.ndarray, ty: np.ndarray,
               date: np.datetime64, inception: np.datetime64) -> tuple:
    """ Function to prepare the cash flows by applying the accrued interest.
    """
    code = get_dt_glob().get('cfC')
    pf, _ = trim_ts(cf, dt, start=date)
    n = len(pf)
    ty, perc = ty[-n:], .0

    if np.isin(code, ty).any():
        cou_idx = np.where(ty == code)[0]
        perc, _, pe = accrued(dt, date, inception)
        pf[cou_idx[0]] *= perc
        pe = pe[-n:]

    else:
        td = np.timedelta64(DAYS_IN_1Y, 'D')
        # t0 = np.datetime64(date, dtype='datetime64[ns]')
        # pe = ((dt - t0) / td)[-n:]
        pe = ((dt - date) / td)[-n:]

    v = np.vstack((pe, pf))

    return v, perc


def calc_fv(dates: Union[np.datetime64, np.ndarray], inception: np.datetime64,
            maturity: np.datetime64, prices: Union[np.ndarray, float],
            cf_values: np.ndarray, cf_dates: np.ndarray, cf_types: np.ndarray,
            rates: float = None):
    _ = prices
    # Quick exit if no dates
    _, dts = trim_ts(None, dates, start=inception, end=maturity)
    n = len(dts)
    if n == 0:
        return np.array([])

    v = np.zeros(n)
    for i in range(n):
        dt, r_, t_ = dts[i], rates, None
        try:
            pf, _ = cash_flows(cf_values, cf_dates, cf_types, dt, inception)
            v[i] = fv(pf, r_, t_)
        except IsNoneError:
            v[i] = np.nan
    return v, dts


def calc_ytm(dates: Union[np.datetime64, np.ndarray], inception: np.datetime64,
             maturity: np.datetime64, prices: Union[np.ndarray, float],
             cf_values: np.ndarray, cf_dates: np.ndarray, cf_types: np.ndarray,
             rates: float = None):
    _ = rates
    return _gen_bm_func('ytm', dates, inception, maturity, prices,
                        cf_values, cf_dates, cf_types)


def calc_duration(dates: Union[np.datetime64, np.ndarray],
                  inception: np.datetime64, maturity: np.datetime64,
                  prices: Union[np.ndarray, float], cf_values: np.ndarray,
                  cf_dates: np.ndarray, cf_types: np.ndarray,
                  rates: float = None):
    _ = rates
    return _gen_bm_func('dur', dates, inception, maturity, prices,
                        cf_values, cf_dates, cf_types)


def calc_convexity(dates: Union[np.datetime64, np.ndarray],
                   inception: np.datetime64, maturity: np.datetime64,
                   prices: Union[np.ndarray, float], cf_values: np.ndarray,
                   cf_dates: np.ndarray, cf_types: np.ndarray,
                   rates: float = None):
    _ = rates
    return _gen_bm_func('cvx', dates, inception, maturity, prices,
                        cf_values, cf_dates, cf_types)


def _gen_bm_func(mode: str, dates: Union[np.datetime64, np.ndarray],
                 inception: np.datetime64, maturity: np.datetime64,
                 prices: Union[np.ndarray, float], cf_values: np.ndarray,
                 cf_dates: np.ndarray, cf_types: np.ndarray):
    if mode == 'ytm':
        f_ = ytm
    elif mode == 'dur':
        f_ = duration
    elif mode == 'cvx':
        f_ = convexity
    else:
        raise ValueError('_gen_bm_func() mode ({}) not recognized'.format(mode))

    if isinstance(prices, float):
        prices = np.array([prices])

    # Quick exit if no dates
    prices, dts = trim_ts(prices, dates, start=inception, end=maturity)
    n = len(dts)
    if n == 0:
        return np.array([])

    v = np.zeros(n)
    for i in range(n):
        dt, p = dts[i], prices[i]
        if np.isnan(p):
            v[i] = np.nan
        else:
            try:
                pf, _ = cash_flows(cf_values, cf_dates, cf_types, dt, inception)
                v[i] = f_(pf, p)
            except IsNoneError:
                v[i] = np.nan
    return v, dts
