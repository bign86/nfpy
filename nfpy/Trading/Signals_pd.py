#
# Signals functions
# Functions to compute signals on pandas dataseries
# The output is a time series for the indicator
#

import numpy as np
import pandas as pd

from nfpy.Calendar import get_calendar_glob


def sma(v: pd.Series, w: int = 21) -> pd.Series:
    """ Simple Moving Average signal.

        Input:
            v [pd.Series]: data series
            w [int]: averaging window (default: 21)
    """
    if len(v) < w:
        raise RuntimeError('Series provided is too short {} < {}'.format(len(v), w))

    m = round(.8 * w)
    ret = v.rolling(w, min_periods=1).mean()
    ret.name = '_'.join(map(str, ['sma', w, get_calendar_glob().frequency]))
    return ret


def smstd(v: pd.Series, w: int = 21) -> pd.Series:
    """ Simple Moving Standard deviation signal.

        Input:
            v [pd.Series]: data series
            w [int]: averaging window (default: 21)
    """
    if len(v) < w:
        raise RuntimeError('Series provided is too short {} < {}'.format(len(v), w))

    m = round(.8 * w)
    ret = v.rolling(w, min_periods=m).std()
    ret.name = '_'.join(map(str, ['smstd', w, get_calendar_glob().frequency]))
    return ret


def csma(v: pd.Series, w: int = 21) -> pd.Series:
    """ Cumulative Simple Moving Average signal.

        Input:
            v [pd.Series]: data series
            w [int]: averaging window (default: 21)
    """
    if len(v) < w:
        raise RuntimeError('Series provided is too short {} < {}'.format(len(v), w))

    ret = v.expanding(min_periods=w).mean()
    ret.name = '_'.join(map(str, ['cma', w, get_calendar_glob().frequency]))
    return ret


def wma(v: pd.Series, w: int = 21) -> pd.Series:
    """ Weighted Moving Average signal.

        Input:
            v [pd.Series]: data series
            w [int]: averaging window (default: 21)
    """
    if len(v) < w:
        raise RuntimeError('Series provided is too short {} < {}'.format(len(v), w))

    def _f(x):
        wgt = np.array([np.nan if np.isnan(x[i]) else i for i in
                        range(x.shape[0])], dtype=float) + 1.
        wgt /= np.nansum(wgt)
        return np.nansum(x * wgt)

    m = round(.8 * w)
    ret = v.rolling(w, min_periods=m)
    ret = ret.apply(_f)
    ret.name = '_'.join(map(str, ['wma', w, get_calendar_glob().frequency]))
    return ret


def ewma(v: pd.Series, w: int = 21, span: int = None) -> pd.Series:
    """ Exponentially Weighted Moving Average signal.

        Input:
            v [pd.Series]: data series
            w [int]: averaging window (default: 21)
            span [int]: Exponential decay (default: w)
    """
    if len(v) < w:
        raise RuntimeError('Series provided is too short {} < {}'.format(len(v), w))

    if not isinstance(v, pd.Series):
        v = pd.Series(v)

    if span is None:
        span = w

    m = round(.8 * w)
    ret = v.ewm(span=span, min_periods=m, adjust=False, ignore_na=True).mean()
    ret.name = '_'.join(map(str, ['ewma', w, get_calendar_glob().frequency]))
    return ret


def mma(v: pd.Series, w: int = 21) -> pd.Series:
    """ Modified Moving Average signal. Corresponds to EWMA with alpha = 1/span.

        Input:
            v [pd.Series]: data series
            w [int]: averaging window (default: 21)
    """
    ret = ewma(v, w, 2 * w - 1)
    ret.name = '_'.join(map(str, ['mma', w, get_calendar_glob().frequency]))
    return ret


def smd(v: pd.Series, w: int = 21) -> pd.Series:
    """ Simple Moving Median signal.

        Input:
            v [pd.Series]: data series
            w [int]: averaging window (default: 21)
    """
    if len(v) < w:
        raise RuntimeError('Series provided is too short {} < {}'.format(len(v), w))

    m = round(.8 * w)
    ret = v.rolling(w, min_periods=m).median()
    ret.name = '_'.join(map(str, ['smd', w, get_calendar_glob().frequency]))
    return ret


def bollinger(v: pd.Series, w: int = 21, rho: float = 2.) -> tuple:
    """ Bollinger Bands signal.

        Input:
            v [pd.Series]: data series
            w [int]: averaging window (default: 21)
            rho [float]: multiplier of the standard deviation

        Output:
            b_down [pd.Series]: the Lower Bollinger band
            b_middle [pd.Series]: the Middle Bollinger band
            b_up [pd.Series]: the Upper Bollinger band
            b_pct [pd.Series]: the %b bandwidth band
            b_width [pd.Series]: the Bandwidth band
    """
    if len(v) < w:
        raise RuntimeError('Series provided is too short {} < {}'.format(len(v), w))

    mean = sma(v, w)
    band_dev = smstd(v, w).multiply(rho)
    low = mean.sub(band_dev)
    up = mean.add(band_dev)
    bdiff = up - low
    bp = (v - low) / bdiff
    bwidth = bdiff / mean

    f = get_calendar_glob().frequency
    low.name = '_'.join(map(str, ['bbUp', w, f]))
    up.name = '_'.join(map(str, ['bbLow', w, f]))
    bp.name = '_'.join(map(str, ['bbPct', w, f]))
    bwidth.name = '_'.join(map(str, ['bbWidth', w, f]))
    return low, mean, up, bp, bwidth


def macd(v: pd.Series, w_fast: int = 12, w_slow: int = 26, w_macd: int = 9)\
        -> tuple:
    """ Moving Average Convergence Divergence signal calculated using EWMAs.

        Input:
            v [pd.Series]: data series
            w_fast [int]: fast window (default: 12)
            w_slow [int]: slow window (default: 26)
            w_macd [int]: averaging window for the signal (default: 9)

        Output:
            macd [pd.Series]: MACD line
            signal [pd.Series]: Signal line
            hist [pd.Series]: Histogram of MACD
            fast_ema [pd.Series]: Fast EWMA used
            slow_ema [pd.Series]: Slow EWMA used
    """
    if w_fast > w_slow:
        w_fast, w_slow = w_slow, w_fast
    elif w_fast == w_slow:
        raise ValueError('Windows for MACD cannot be equal')

    if w_macd >= w_fast:
        raise ValueError('MACD window should be smaller than fast SMA window')

    if len(v) < w_slow:
        raise RuntimeError('Series provided is too short {} < {}'.format(len(v), w_slow))

    fast_ema = ewma(v, w_fast)
    slow_ema = ewma(v, w_slow)
    macd_l = fast_ema - slow_ema
    signal = ewma(macd_l, w_macd)
    hist = macd_l - signal

    f = get_calendar_glob().frequency
    macd_l.name = '_'.join(map(str, ['macd', w_fast, w_slow, f]))
    signal.name = '_'.join(map(str, ['macdSignal', w_macd, f]))
    hist.name = '_'.join(map(str, ['macdHist', w_fast, w_slow, w_macd, f]))
    return macd_l, signal, hist, fast_ema, slow_ema


def _rsi(v: pd.Series, w: int, mode: str) -> pd.Series:
    """ Relative Strength Index signal calculation """
    if mode == 'ewma':
        ma_function = mma
    elif mode == 'sma':
        ma_function = sma
    else:
        raise ValueError('RSI mode {} not recognized'.format(mode))

    up_v, down_v = v.copy(), v.copy()
    up_v[up_v < 0.] = 0.
    down_v[down_v > 0.] = 0.

    plus = ma_function(up_v, w)
    minus = ma_function(down_v.abs(), w)
    rs = plus / minus
    rsi = 1. - 1. / (1. + rs)

    rsi.name = '_'.join(map(str, ['rsi', w, mode]))
    return rsi


def wilder_rsi(v: pd.Series, w: int = 14) -> pd.Series:
    """ Wilder's Relative Strength Index signal using the exponential averaging.

        Input:
            v [pd.Series]: return data series
            w [int]: rolling window (default: 14)

        Output:
            rsi [pd.Series]: RSI signal
    """
    return _rsi(v, w, mode='ewma')


def cutler_rsi(v: pd.Series, w: int = 14) -> pd.Series:
    """ Cutler's Relative Strength Index signal using the simple averaging.

        Input:
            v [pd.Series]: return data series
            w [int]: rolling window (default: 14)

        Output:
            rsi [pd.Series]: RSI signal
    """
    return _rsi(v, w, mode='sma')


def stochastic_oscillator(v: pd.Series, w_price: int = 14, w_k: int = 3,
                             w_d: int = 5) -> tuple:
    """ Stochastic Oscillator.

        Input:
            v [pd.Series]: price data series
            w_price [int]: rolling window on price series (default: 14)
            w_k [int]: rolling window on %K (default: 3)
            w_d [int]: rolling window on %D (default: 5)

        Output:
            d_p [pd.Series]: oscillator signal
            dp_slow [pd.Series]: SMA of the oscillator signal
    """
    roll = v.rolling(w_price, min_periods=1)
    high, low = roll.max(), roll.min()
    p_k = (v - low) / (high - low)
    d_p = p_k.rolling(w_k, min_periods=1).mean()
    dp_slow = d_p.rolling(w_d, min_periods=1).mean()

    d_p.name = '_'.join(map(str, ['stchOscill', w_price, w_k]))
    dp_slow.name = '_'.join(map(str, ['stchOscill', w_price, w_k, w_d]))
    return d_p, dp_slow
