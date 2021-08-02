#
# Indicator functions
# Functions to compute indicators on time series. The output is a time series
# for the indicator.
#

import numpy as np

import nfpy.Financial.Math as Math
from nfpy.Tools import Exceptions as Ex


def _check_len(v, w) -> None:
    l = len(v)
    if l < w:
        raise Ex.ShortSeriesError(f'Series provided is too short {l} < {w}')


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


def sma_approx(v: np.ndarray, w: int) -> np.ndarray:
    """ Simple Moving Average signal. Online approximate algorithm.

        Input:
            v [np.ndarray]: data series
            w [int]: averaging window
    """
    _check_len(v, w)

    ret = v.copy()
    curr, idx = Math.next_valid_value(v)

    for i in range(idx + 1, len(v)):
        _v = ret[i]
        if _v == _v:
            curr += (_v - curr) / w
        ret[i] = curr

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


def csma(v: np.ndarray, w: int) -> np.ndarray:
    """ Cumulative Simple Moving Average indicator.

        Input:
            v [np.ndarray]: data series
            w [int]: averaging window
    """
    _check_len(v, w)

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


def ewma_other_version(v: np.ndarray, w: int) -> np.ndarray:
    """ Exponentially Weighted Moving Average indicator.

        Input:
            v [pd.Series]: data series
            w [int]: averaging window
    """
    _check_len(v, w)

    alpha = 2. / (w + 1)
    alpha_rev = 1. - alpha
    n = v.shape[0]

    pows = alpha_rev ** (np.arange(n + 1))

    scale_arr = 1. / pows[:-1]
    offset = v[0] * pows[1:]
    pw0 = alpha * alpha_rev ** (n - 1)

    mult = v * pw0 * scale_arr
    cumsums = np.cumsum(mult)
    ret = offset + cumsums * scale_arr[::-1]

    return ret


def ewma(v: np.ndarray, w: int, span: int = None) -> np.ndarray:
    """ Exponentially Weighted Moving Average indicator.

        Input:
            v [np.ndarray]: data series
            w [int]: averaging window
    """
    if w:
        alpha = 2. / (1. + w)
    elif span:
        alpha = 1. / (1. + span)
    else:
        raise ValueError('Either one of w and span must be specified')

    n = len(v)
    coeff = 1. - alpha

    fv = Math.next_valid_index(v)
    curr = v[fv]

    ret = np.empty(n)
    ret[:fv] = np.nan
    ret[fv] = curr
    ret[fv + 1:] = alpha * v[fv + 1:]

    for i in range(fv + 1, n):
        _v = ret[i]
        if _v == _v:
            curr = _v + coeff * curr
        ret[i] = curr

    return ret


def mma(v: np.ndarray, w: int) -> np.ndarray:
    """ Modified Moving Average indicator. Corresponds to EWMA with
            alpha = 1/span.

        Input:
            v [np.ndarray]: data series
            w [int]: averaging window
    """
    return ewma(v, w, 2 * w - 1)


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


def bollinger(v: np.ndarray, w: int, rho: float) -> tuple:
    """ Bollinger Bands indicator.

        Input:
            v [np.ndarray]: data series
            w [int]: averaging window
            rho [float]: multiplier of the standard deviation

        Output:
            b_down [np.ndarray]: the Lower Bollinger band
            b_middle [np.ndarray]: the Middle Bollinger band
            b_up [np.ndarray]: the Upper Bollinger band
            b_pct [np.ndarray]: the %b bandwidth band
            b_width [np.ndarray]: the Bandwidth band
    """
    _check_len(v, w)

    mean = sma(v, w)
    band_dev = rho * smstd(v, w)
    low = mean - band_dev
    up = mean + band_dev
    bdiff = up - low
    bp = (v - low) / bdiff
    bwidth = bdiff / mean

    return low, mean, up, bp, bwidth


def macd(v: np.ndarray, w_macd: int, w_fast: int, w_slow: int) -> tuple:
    """ Moving Average Convergence Divergence indicator calculated using EWMAs.

        Input:
            v [np.ndarray]: data series
            w_macd [int]: averaging window for the indicator
            w_fast [int]: fast window
            w_slow [int]: slow window

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


def _rsi(v: np.ndarray, w: int, mode: str) -> np.ndarray:
    """ Relative Strength Index indicator calculation. """
    if mode == 'ewma':
        ma_function = mma
    elif mode == 'sma':
        ma_function = sma
    else:
        raise ValueError(f'RSI mode {mode} not recognized')

    up_v, down_v = v.copy(), v.copy()
    up_v[up_v < 0.] = 0.
    down_v[down_v > 0.] = 0.

    plus = ma_function(up_v, w)
    minus = ma_function(down_v.abs(), w)
    rs = plus / minus

    return 1. - 1. / (1. + rs)


def wilder_rsi(v: np.ndarray, w: int) -> np.ndarray:
    """ Wilder's Relative Strength Index indicator using the EWMA.

        Input:
            v [np.ndarray]: return data series
            w [int]: rolling window

        Output:
            rsi [np.ndarray]: RSI signal
    """
    return _rsi(v, w, mode='ewma')


def cutler_rsi(v: np.ndarray, w: int) -> np.ndarray:
    """ Cutler's Relative Strength Index indicator using the SMA.

        Input:
            v [np.ndarray]: return data series
            w [int]: rolling window

        Output:
            rsi [np.ndarray]: RSI signal
    """
    return _rsi(v, w, mode='sma')


def stochastic_oscillator(v: np.ndarray, w_price: int = 14, w_k: int = 3,
                          w_d: int = 5) -> tuple:
    """ Stochastic Oscillator.

        Input:
            v [np.ndarray]: price data series
            w_price [int]: rolling window on price series (default: 14)
            w_k [int]: rolling window on %K (default: 3)
            w_d [int]: rolling window on %D (default: 5)

        Output:
            d_p [np.ndarray]: stochastic oscillator
            dp_slow [np.ndarray]: SMA of the oscillator
    """
    if w_k > w_d:
        w_k, w_d = w_d, w_k

    roll = Math.rolling_window(v, w_price)
    high = np.nanmax(roll, axis=1)
    low = np.nanmin(roll, axis=1)
    p_k = (v[w_price - 1:] - low) / (high - low)

    d_p = np.empty_like(v)
    dp_slow = np.empty_like(v)
    n_dp = w_price + w_k - 2
    n_dp_slow = w_price + w_d

    d_p[:n_dp] = np.nan
    dp_slow[:n_dp_slow] = np.nan

    d_p[n_dp:] = np.nanmean(
        Math.rolling_window(p_k, w_k),
        axis=1
    )
    dp_slow[n_dp_slow:] = np.nanmean(
        Math.rolling_window(d_p[n_dp:], w_d),
        axis=1
    )

    return d_p, dp_slow


def tr(ts: np.ndarray) -> np.ndarray:
    """ Calculates the True Range (TR) as the maximum between:
            1. abs(high_{t} - low_{t})
            2. abs(high_{t} - close_{t-1})
            3. abs(low_{t} - close_{t-1})
        The ts array is expected with shape (3, n) with each row representing
        high, low, close respectively. If an array with shape (1, n) or (n,) is
        provided, is immediately returned.

        Input:
            ts [np.ndarray]: input candles

        Output:
            tr [np.ndarray]: true range
    """
    if len(ts.shape) == 1:
        return np.abs(ts[1:] - ts[:-1])
    elif (len(ts.shape) == 2) and (ts.shape[0] == 3):
        # return np.maximum(
        #     np.maximum(
        #         np.abs(ts[0, 1:] - ts[1, 1:]),
        #         np.abs(ts[0, 1:] - ts[2, :-1])
        #     ),
        #     np.abs(ts[1, 1:] - ts[2, :-1])
        # )
        return np.maximum(ts[0, 1:], ts[2, :-1]) - \
               np.minimum(ts[1, 1:], ts[2, :-1])
    else:
        raise ValueError("Input malformed: true_range.shape != (n,) or (3, n)")


def atr_win(ts: np.ndarray, w: int) -> np.ndarray:
    """ Calculates the Average True Range over the given window. The ts array is
        expected with shape (3, n) with each row representing respectively high,
        low, close. If an array with shape (1, n) or (n,) is provided, the
        normal volatility is calculated as a backup solution.

        Input:
            ts [np.ndarray]: input candles
            w [int]: rolling window size

        Output:
            tr [np.ndarray]: average true range
    """
    ret = np.zeros_like(ts)
    ret[:w] = np.nan
    ret[w:] = Math.rolling_mean(tr(ts), w)
    return ret


def atr(ts: np.ndarray, w: int) -> np.ndarray:
    """ Calculates the Average True Range over the given window. The ts array is
        expected with shape (3, n) with each row representing respectively high,
        low, close. If an array with shape (1, n) or (n,) is provided, the
        normal volatility is calculated as a backup solution.

        Input:
            ts [np.ndarray]: input candles
            w [int]: rolling window size (default 14)

        Output:
            tr [np.ndarray]: average true range
    """
    t = Math.ffill_cols(tr(ts))
    ret = np.empty(ts.shape[0])

    curr = np.nanmean(t)
    ret[0] = curr
    for i in range(t.shape[0]):
        curr = ((w - 1) * curr + t[i]) / w
        ret[i + 1] = curr

    return ret


def tsi(ret: np.ndarray, w_fast: int, w_slow: int) -> np.ndarray:
    """ Calculates the Average True Range over the given window. The ts array is
        expected with shape (3, n) with each row representing respectively high,
        low, close. If an array with shape (1, n) or (n,) is provided, the
        normal volatility is calculated as a backup solution.

        Input:
            ts [np.ndarray]: input return series
            w_fast [int]: short rolling window size
            w_slow [int]: long rolling window size

        Output:
            tsi [np.ndarray]: True Strength Index
    """
    d = np.empty_like(ret)
    d[0] = np.nan
    d[1:] = ret[:-1] - ret[1:]
    fs = ewma(d, w_slow)
    pc = ewma(fs, w_fast)

    fs = ewma(np.abs(d), w_slow)
    apc = ewma(fs, w_fast)

    return 100. * (pc / apc)


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
