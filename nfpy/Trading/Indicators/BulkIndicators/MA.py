#
# Moving Average Indicators
# Moving Average based indicators in bulk form.
#

import numpy as np

import nfpy.Math as Math

from ..Utils import _check_len


def sma(v: np.ndarray, w: int) -> np.ndarray:
    """ Simple Moving Average indicator. Windowed algorithm.

        Input:
            v [np.ndarray]: data series
            w [int]: averaging window
    """
    _check_len(v, w)

    ret = np.empty_like(v)
    ret[:w - 1] = np.nan
    ret[w - 1:] = Math.rolling_mean(v, w)

    return ret


def smstd(v: np.ndarray, w: int, ddof: int = 1) -> np.ndarray:
    """ Simple Moving Standard deviation indicator.

        Input:
            v [np.ndarray]: data series
            w [int]: averaging window
            ddof [int]: degrees of freedom (default: 1 to emulate pandas)
    """
    _check_len(v, w)

    ret = np.empty_like(v)
    ret[:w - 1] = np.nan
    ret[w - 1:] = np.nanstd(Math.rolling_window(v, w), axis=1, ddof=ddof)

    return ret


def csma(v: np.ndarray) -> np.ndarray:
    """ Cumulative Simple Moving Average indicator.

        Input:
            v [np.ndarray]: data series
    """
    # ret = np.empty_like(div)
    # ret[0] = v[0]
    # for i, d in enumerate(v, 1):
    #     ret[i] = (v[i] - v[i - 1]) / (i + 1)
    _sum = np.nancumsum(v)
    _div = np.cumsum(~np.isnan(v))

    return _sum / _div


def wma(v: np.ndarray, w: int) -> np.ndarray:
    """ Weighted Moving Average indicator.

        Input:
            v [np.ndarray]: data series
            w [int]: averaging window
    """
    _check_len(v, w)

    roll = Math.rolling_window(v, w)
    nans = np.isnan(roll)
    wgt = np.tile(np.arange(1., roll.shape[1] + 1.), (roll.shape[0], 1))
    wgt[nans] = .0
    wgt /= np.sum(wgt, axis=1, keepdims=True)

    ret = np.empty_like(v)
    ret[:w - 1] = np.nan
    ret[w - 1:] = np.nansum(roll * wgt, axis=1)

    return ret


def ewma_vec(v: np.ndarray, w: int) -> np.ndarray:
    """ Exponentially Weighted Moving Average indicator.
        Note: this version does not contain explicit loops, however it does have
              some numerical stability problems.

        Input:
            v [pd.Series]: data series
            w [int]: averaging window
    """
    _check_len(v, w)

    alpha = 2. / (1. + w)
    alpha_rev = 1. - alpha
    n = v.shape[0]

    pows = alpha_rev ** (np.arange(n + 1))

    scale_arr = 1. / pows[:-1]
    offset = v[0] * pows[1:]
    pw0 = alpha * alpha_rev ** (n - 1)

    mult = v * pw0 * scale_arr
    cumsums = np.nancumsum(mult)
    ret = offset + cumsums * scale_arr[::-1]

    return ret


def ewma(v: np.ndarray, w: int) -> np.ndarray:
    """ Exponentially Weighted Moving Average indicator.
        Note: this version does contain an explicit loop making it less
            efficient, however it does NOT show numerical stability problems.

        Input:
            v [np.ndarray]: data series
            w [int]: averaging window
    """
    alpha = 2. / (1. + w)
    coeff = 1. - alpha

    fv = Math.next_valid_index(v)
    curr = v[fv]

    ret = np.empty_like(v)
    ret[:fv] = np.nan
    ret[fv] = curr
    ret[fv + 1:] = alpha * v[fv + 1:]

    for i in range(fv + 1, v.shape[0]):
        _v = ret[i]
        if _v == _v:
            curr = _v + coeff * curr
        ret[i] = curr

    return ret


def smd(v: np.ndarray, w: int) -> np.ndarray:
    """ Simple Moving Median indicator.

        Input:
            v [np.ndarray]: data series
            w [int]: averaging window
    """
    _check_len(v, w)

    ret = np.empty_like(v)
    ret[:w - 1] = np.nan
    ret[w - 1:] = np.nanmedian(Math.rolling_window(v, w), axis=1)
    return ret


def macd(v: np.ndarray, w_slow: int, w_fast: int, w_macd: int) -> tuple:
    """ Moving Average Convergence Divergence indicator calculated using EWMAs.

        Input:
            v [np.ndarray]: data series
            w_slow [int]: slow window
            w_fast [int]: fast window
            w_macd [int]: averaging window for the indicator

        Output:
            macd [np.ndarray]: MACD line
            signal [np.ndarray]: Signal line
            hist [np.ndarray]: Histogram of MACD
            fast_ema [np.ndarray]: Fast EWMA used
            slow_ema [np.ndarray]: Slow EWMA used
    """
    if w_fast > w_slow:
        w_fast, w_slow = w_slow, w_fast
    elif w_fast == w_slow:
        raise ValueError('Windows for MACD cannot be equal')
    if w_macd >= w_fast:
        raise ValueError('MACD window should be smaller than fast EMA window')

    _check_len(v, w_slow)

    fast_ema = ewma(v, w_fast)
    slow_ema = ewma(v, w_slow)
    _macd = fast_ema - slow_ema
    signal = ewma(_macd, w_macd)
    hist = _macd - signal

    return _macd, signal, hist, fast_ema, slow_ema


def dema(v: np.ndarray, w: int) -> np.ndarray:
    """ Double Exponential Moving Average. Trend indicator. The EMAs are
        calculated in waterfall. The date series dt is not used.

        Input:
            v [np.ndarray]: price series
            w [int]: rolling window size

        Output:
            tema [np.ndarray]: double EMA
    """
    ema_1 = ewma(v, w)
    ema_2 = ewma(ema_1, w)

    return 2. * ema_1 - ema_2


def tema(v: np.ndarray, w: int) -> np.ndarray:
    """ Triple Exponential Moving Average. Trend indicator. The EMAs are
        calculated in waterfall. The date series dt is not used.

        Input:
            v [np.ndarray]: price series
            w [int]: rolling window size

        Output:
            tema [np.ndarray]: triple EMA
    """
    ema_1 = ewma(v, w)
    ema_2 = ewma(ema_1, w)
    ema_3 = ewma(ema_2, w)

    return 3. * ema_1 - 3. * ema_2 + ema_3
