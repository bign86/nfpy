#
# Bond math functions
# Functions with bond math
#

import numpy as np
from scipy.optimize import newton
from typing import Union

from nfpy.DatatypeFactory import get_dt_glob
from nfpy.Tools import (Constants as Cn, Exceptions as Ex)

from .DiscountFactor import dcf
from .EquityMath import fv
from .TSUtils import trim_ts


def ytm(cf: np.ndarray, p0: float, acc: float = .0) -> float:
    """ Calculates the YTM using the cash flows and market price, taking into
        account the presence of accrued interest.

        Input:
            cf [np.ndarray]: data (periods, value) of cash flows
            p0 [float]: market price at t0
            accrued [float]: accrued interest to subtract from dirty price

        Output:
            res [float]: yield to maturity
    """
    def _min_ytm(r, dt):
        return fv(dt, r, None, acc) - p0

    return newton(_min_ytm, .02, args=(cf,))


def __time_cf(cf: np.ndarray, p0: float, acc: float, exp: float) -> float:
    _ytm = ytm(cf, p0, acc)
    wflow = dcf(cf, _ytm) * (cf[0, :] ** exp)
    return float(wflow.sum()) / p0


def duration(cf: np.ndarray, p0: float, acc: float = .0) -> float:
    """ Calculates the bond duration from the cash flows and the market price,
        taking into account the presence of accrued interest.

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
            pe [np.ndarray]:
    """
    td = np.timedelta64(Cn.DAYS_IN_1Y, 'D')

    # Find the relevant cash flows
    pe = (dt - t0) / td
    t0_idx = np.where(np.diff(np.sign(pe) > 0))[0]

    # If there is no index found we accrue since inception
    if len(t0_idx) == 0:
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

        Input:
            cf [np.ndarray]: array of cash flows
            dt [np.ndarray]: array of cash flow dates
            ty [np.ndarray]: array of cash flow types
            date: [np.datetime64]: reference date
            inception [np.datetime64]: inception date of the bond

        Output:
            v [np.ndarray]: array of time distances in years from cash flows and
                cash flow values including accrued interest
            dt [np.ndarray]: array of dates
            perc [float]: percentage of cash flow accrued
    """
    code = get_dt_glob().get('cfC')
    pf, dts = trim_ts(cf, dt, start=date)
    n = len(pf)
    ty, perc = ty[-n:], .0

    if np.isin(code, ty).any():
        cou_idx = np.where(ty == code)[0]
        perc, _, pe = accrued(dt, date, inception)
        pf[cou_idx[0]] *= perc
        pe = pe[-n:]

    else:
        td = np.timedelta64(Cn.DAYS_IN_1Y, 'D')
        pe = ((dt - date) / td)[-n:]

    v = np.vstack((pe, pf))

    return v, dts, perc


def calc_fv(dates: Union[np.datetime64, np.ndarray], inception: np.datetime64,
            maturity: np.datetime64, prices: Union[np.ndarray, float],
            cf_values: np.ndarray, cf_dates: np.ndarray, cf_types: np.ndarray,
            rates: Union[np.ndarray, float]) -> tuple:
    """ Function to calculate the fair value of a bond given the cash flows.

        Input:
            dates [Union[np.datetime64, np.ndarray]]: array of cash flow dates
            inception [np.datetime64]: inception date of the bond
            maturity [np.datetime64]: maturity date of the bond
            prices [Union[np.ndarray, float]]: array of prices prices
                (only for signature consistency)
            cf_values [np.ndarray]: array of cash flows
            cf_dates [np.ndarray]: array of cash flow dates
            cf_types [np.ndarray]: array of cash flow types
            rates: [Union[np.ndarray, float]]: discount rate

        Output:
            v [np.ndarray]: array of fair values
            dts [np.ndarray]: array of dates
    """
    # Prepare input data
    _ = prices
    is_single_date = isinstance(dates, np.datetime64)
    is_single_rate = isinstance(rates, float)
    if is_single_date & is_single_rate:
        dates = np.array([dates])
        rates = np.array([rates])
    elif is_single_rate:
        rates = np.array([rates] * len(dates))
    elif is_single_date:
        dates = np.array([dates] * len(rates))

    # Quick exit if no dates
    _, dts = trim_ts(None, dates, start=inception, end=maturity)
    n = len(dts)
    if n == 0:
        return np.array([]), np.array([])

    v = np.empty(n)
    for i in range(n):
        dt, r_, t_ = dts[i], rates[i], None
        try:
            pf, _, _ = cash_flows(cf_values, cf_dates, cf_types, dt, inception)
            v[i] = fv(pf, r_, t_)
        except Ex.IsNoneError:
            v[i] = np.nan
    return v, dts


def calc_ytm(dates: Union[np.datetime64, np.ndarray], inception: np.datetime64,
             maturity: np.datetime64, prices: Union[np.ndarray, float],
             cf_values: np.ndarray, cf_dates: np.ndarray, cf_types: np.ndarray,
             rates: Union[np.ndarray, float]) -> tuple:
    """ Function to calculate the yield to maturity of a bond given the cash flows.

        Input:
            dates [Union[np.datetime64, np.ndarray]]: array of cash flow dates
            inception [np.datetime64]: inception date of the bond
            maturity [np.datetime64]: maturity date of the bond
            prices [Union[np.ndarray, float]]: array of prices prices
            cf_values [np.ndarray]: array of cash flows
            cf_dates [np.ndarray]: array of cash flow dates
            cf_types [np.ndarray]: array of cash flow types
            rates: [Union[np.ndarray, float]]: discount rate
                (only for signature consistency)

        Output:
            v [np.ndarray]: array of fair values
            dts [np.ndarray]: array of dates
    """
    _ = rates
    return _gen_bm_func('ytm', dates, inception, maturity, prices,
                        cf_values, cf_dates, cf_types)


def calc_duration(dates: Union[np.datetime64, np.ndarray],
                  inception: np.datetime64, maturity: np.datetime64,
                  prices: Union[np.ndarray, float], cf_values: np.ndarray,
                  cf_dates: np.ndarray, cf_types: np.ndarray,
                  rates: Union[np.ndarray, float]) -> tuple:
    """ Function to calculate the duration of a bond given the cash flows.

        Input:
            dates [Union[np.datetime64, np.ndarray]]: array of cash flow dates
            inception [np.datetime64]: inception date of the bond
            maturity [np.datetime64]: maturity date of the bond
            prices [Union[np.ndarray, float]]: array of prices prices
                (only for signature consistency)
            cf_values [np.ndarray]: array of cash flows
            cf_dates [np.ndarray]: array of cash flow dates
            cf_types [np.ndarray]: array of cash flow types
            rates: [Union[np.ndarray, float]]: discount rate
                (only for signature consistency)

        Output:
            v [np.ndarray]: array of fair values
            dts [np.ndarray]: array of dates
    """
    _ = rates
    return _gen_bm_func('dur', dates, inception, maturity, prices,
                        cf_values, cf_dates, cf_types)


def calc_convexity(dates: Union[np.datetime64, np.ndarray],
                   inception: np.datetime64, maturity: np.datetime64,
                   prices: Union[np.ndarray, float], cf_values: np.ndarray,
                   cf_dates: np.ndarray, cf_types: np.ndarray,
                   rates: Union[np.ndarray, float]) -> tuple:
    """ Function to calculate the convexity of a bond given the cash flows.

        Input:
            dates [Union[np.datetime64, np.ndarray]]: array of cash flow dates
            inception [np.datetime64]: inception date of the bond
            maturity [np.datetime64]: maturity date of the bond
            prices [Union[np.ndarray, float]]: array of prices prices
                (only for signature consistency)
            cf_values [np.ndarray]: array of cash flows
            cf_dates [np.ndarray]: array of cash flow dates
            cf_types [np.ndarray]: array of cash flow types
            rates: [Union[np.ndarray, float]]: discount rate
                (only for signature consistency)

        Output:
            v [np.ndarray]: array of fair values
            dts [np.ndarray]: array of dates
    """
    _ = rates
    return _gen_bm_func('cvx', dates, inception, maturity, prices,
                        cf_values, cf_dates, cf_types)


def _gen_bm_func(mode: str, dates: Union[np.datetime64, np.ndarray],
                 inception: np.datetime64, maturity: np.datetime64,
                 prices: Union[np.ndarray, float], cf_values: np.ndarray,
                 cf_dates: np.ndarray, cf_types: np.ndarray) -> tuple:
    """ General function to calculate fair value, duration and convexity of a
        bond given the bond' cash flows, and maturity and inception dates.
    """
    # Prepare input data
    is_single_date = isinstance(dates, np.datetime64)
    is_single_rate = isinstance(prices, float)
    if is_single_date & is_single_rate:
        dates = np.array([dates])
        prices = np.array([prices])
    elif is_single_rate:
        prices = np.array([prices] * len(dates))
    elif is_single_date:
        dates = np.array([dates] * len(prices))

    # Select calculation
    if mode == 'ytm':
        f_ = ytm
    elif mode == 'dur':
        f_ = duration
    elif mode == 'cvx':
        f_ = convexity
    else:
        raise ValueError('_gen_bm_func() mode ({}) not recognized'.format(mode))

    # Trim data
    prices, dts = trim_ts(prices, dates, start=inception, end=maturity)
    n = len(dts)
    if n == 0:
        # Quick exit if no dates
        return np.array([]), np.array([])

    v = np.empty(n)
    for i in range(n):
        dt, p = dts[i], prices[i]
        if np.isnan(p):
            v[i] = np.nan
        else:
            try:
                pf, _, _ = cash_flows(cf_values, cf_dates, cf_types, dt, inception)
                v[i] = f_(pf, p)
            except Ex.IsNoneError:
                v[i] = np.nan
    return v, dts


def calc_dcf(date: np.datetime64, inception: np.datetime64,
             maturity: np.datetime64, cf_values: np.ndarray,
             cf_dates: np.ndarray, cf_types: np.ndarray,
             rates: Union[np.ndarray, float]) -> tuple:
    """ Function to prepare the cash flows by applying the accrued interest.

        Input:
            date: [np.datetime64]: reference date
            inception [np.datetime64]: inception date of the bond
            maturity [np.datetime64]: maturity date of the bond
            cf_values [np.ndarray]: array of cash flows
            cf_dates [np.ndarray]: array of cash flow dates
            cf_types [np.ndarray]: array of cash flow types
            rates: [Union[np.ndarray, float]]: discount rate

        Output:
            v [np.ndarray]: array of fair values
            dt [np.ndarray]: array of dates
    """
    if isinstance(rates, float):
        rates = np.array([rates])
    dates = np.array([date])

    # Quick exit if no dates
    _, dts = trim_ts(None, dates, start=inception, end=maturity)
    if len(dts) == 0:
        return np.array([]), np.array([])

    pf, dt, _ = cash_flows(cf_values, cf_dates, cf_types, dts[0], inception)

    m = len(rates)
    v = np.empty((m, pf.shape[1]))
    for i in range(m):
        try:
            v[i, :] = dcf(pf, rates[i], None)
        except Ex.IsNoneError:
            v[i, :] = np.nan
    return v, dt


def aggregate_cf(cf_values: np.ndarray, cf_dates: np.ndarray) -> tuple:
    """ Function to aggregate the cash flows by date.

        Input:
            cf_values [np.ndarray]: array of cash flows
            cf_dates [np.ndarray]: array of cash flow dates

        Output:
            ret [np.ndarray]: array of aggregated cash flows
            dt [np.ndarray]: array of dates
    """
    dim_1 = True if len(cf_values.shape) == 1 else False
    cf_dt_unique = np.unique(cf_dates)

    if dim_1:
        cf_values = cf_values[None, :]

    ret = np.zeros((cf_values.shape[0], cf_dt_unique.shape[0]))
    last_cf_date, j = None, 0
    for i in range(cf_dates.shape[0]):
        dt = cf_dates[i]
        if dt == last_cf_date:
            j -= 1
        last_cf_date = dt
        ret[:, j] += cf_values[:, i]
        j += 1

    # This version takes the double of the time of the previous
    # ret = np.empty((cf_values.shape[0], cf_dt_unique.shape[0]))
    # for i, d in enumerate(cf_dt_unique):
    #     ret[:, i] = np.sum(cf_values[:, np.where(cf_dates == d)[0]], axis=1)

    if dim_1:
        ret = np.ravel(ret)

    return ret, cf_dt_unique
