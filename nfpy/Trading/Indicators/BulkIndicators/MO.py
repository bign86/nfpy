#
# Momentum Oscillator Indicators
# Momentum Oscillator based indicators in bulk form.
#

import numpy as np
from typing import Callable

import nfpy.Math as Math

from .MA import (ewma, sma)
from ..Utils import _check_len


def atr(ts: np.ndarray, w: int) -> np.ndarray:
    """ Calculates the Average True Range over the given window. The <ts> array
        is expected to have shape (3, n) with each row having the structure:
            <high, low, close>.
        If an array with shape (n,) is provided, the normal volatility is
        calculated as a backup solution.

        Input:
            ts [np.ndarray]: input candles
            w [int]: rolling window size

        Output:
            tr [np.ndarray]: average true range
    """
    _check_len(ts, w)

    t = Math.ffill_cols(tr(ts))
    v_atr = np.empty(ts.shape[0])

    curr = np.nanmean(t)
    v_atr[0] = curr
    for i in range(t.shape[0]):
        curr = ((w - 1) * curr + t[i]) / w
        v_atr[i + 1] = curr

    return v_atr


def atr_win(ts: np.ndarray, w: int) -> np.ndarray:
    """ Calculates the Average True Range over the given window. The <ts> array
        is expected to have shape (3, n) with each row having the structure:
            <high, low, close>.
        If an array with shape (1, n) or (n,) is provided, the
        normal volatility is calculated as a backup solution.

        Input:
            ts [np.ndarray]: input candles
            w [int]: rolling window size

        Output:
            tr [np.ndarray]: average true range
    """
    _check_len(ts, w)

    v_atr = np.zeros_like(ts)
    v_atr[:w] = np.nan
    v_atr[w:] = Math.rolling_mean(tr(ts), w)
    return v_atr


def cci(p: np.ndarray, w: int) -> np.ndarray:
    """ Calculates the Commodity Channel Index indicator.

        Input:
            p [np.ndarray]: input prices
            w [int]: rolling window size

        Output:
            cci [np.ndarray]: series of the indicator
    """
    _check_len(p, w)

    dmean = p - sma(p, w)
    mad = Math.rolling_mean_ad(p, w)

    v_cci = np.empty(p.shape[0])
    v_cci[:w - 1] = np.nan
    v_cci[w - 1:] = dmean[w - 1:] / (.015 * mad)

    return v_cci


def fi(ts: np.ndarray, *args) -> np.ndarray:
    """ Force Index indicator calculation. It is the price difference scaled by
        the trade volume. The input must be like:
            <price, volume>.

        Input:
            p [np.ndarray]: input prices and volumes

        Output:
            fi [np.ndarray]: series of the FI indicator
    """
    _ = args
    return np.r_[np.nan, np.diff(ts[0, :]) * ts[1, 1:]]


def fi_elder(ts: np.ndarray, w: int) -> np.ndarray:
    """ Elder's Force Index indicator calculation. It is the moving average of
        the price difference scaled by the trade volume. The input must be like:
            <price, volume>.

        Input:
            ts [np.ndarray]: input prices and volumes
            w [int]: rolling window size (typical 13 periods)

        Output:
            fi [np.ndarray]: series of the FI indicator
    """
    _check_len(ts, w)

    v = np.r_[np.nan, np.diff(ts[0, :]) * ts[1, 1:]]
    return sma(v, w)


def mfi(ts: np.ndarray, w: int) -> np.ndarray:
    """ Money Flow Index indicator calculation. The <ts> array is expected to
        have a shape like (2, n) or (4, n) with each row having the structure:
            <close, volume> or <high, low, close, volume>.

        Input:
            ts [np.ndarray]: input candles or prices and volumes
            w [int]: rolling window size (typical 14 periods)
    """
    if ts.shape[0] == 2:
        tp = ts[0, :]
    elif ts.shape[0] == 4:
        tp = np.sum(ts[:3, :], axis=1) / 3.
    else:
        raise ValueError("mfi(): Input malformed: ts.shape != (n,) or (3, n)")
    _check_len(ts, w)

    raw_money_flow = np.diff(tp * ts[3, :])
    pos_money_flow = np.where(raw_money_flow > .0, 1, 0)
    neg_money_flow = np.where(raw_money_flow < .0, 1, 0)

    roll_pos_mf = Math.rolling_sum(pos_money_flow, w)
    roll_neg_mf = Math.rolling_sum(neg_money_flow, w)
    mf = roll_pos_mf / roll_neg_mf

    mf_index = 100. - 100. / (1. + mf)
    v_mfi = np.r_[[np.nan] * w, mf_index]
    assert len(v_mfi) == ts.shape[1], f"{len(v_mfi)} != {ts.shape[1]}"

    return v_mfi


def _rsi(v: np.ndarray, w: int, ma_f: Callable) -> np.ndarray:
    """ Relative Strength Index indicator calculation. """
    up_d = np.diff(v)
    down_d = -np.copy(up_d)
    up_d[up_d < 0.] = 0.
    down_d[down_d < 0.] = 0.

    rs = ma_f(up_d, w) / ma_f(down_d, w)
    return np.r_[[np.nan] * w, 100. - 100. / (1. + rs)]


def rsi_cutler(v: np.ndarray, w: int) -> np.ndarray:
    """ Cutler's Relative Strength Index indicator using the SMA.

        Input:
            v [np.ndarray]: return data series
            w [int]: rolling window

        Output:
            rsi [np.ndarray]: RSI signal
    """
    _check_len(v, w)
    return _rsi(v, w, ma_f=sma)


def rsi_wilder(v: np.ndarray, w: int) -> np.ndarray:
    """ Wilder's Relative Strength Index indicator using the EWMA.

        Input:
            v [np.ndarray]: return data series
            w [int]: rolling window

        Output:
            rsi [np.ndarray]: RSI signal
    """
    _check_len(v, w)
    return _rsi(v, w, ma_f=ewma)


def stochastic(v: np.ndarray, w_price: int, w_k: int, w_d: int) -> tuple:
    """ Stochastic Oscillator.

        Input:
            v [np.ndarray]: price data series
            w_price [int]: rolling window on price series
            w_k [int]: rolling window on %K
            w_d [int]: rolling window on %D

        Output:
            d_p [np.ndarray]: stochastic oscillator
            dp_slow [np.ndarray]: SMA of the oscillator
    """
    _check_len(v, w_price+w_k)

    if w_k > w_d:
        w_k, w_d = w_d, w_k

    roll = Math.rolling_window(v, w_price)
    high = np.nanmax(roll, axis=1)
    low = np.nanmin(roll, axis=1)
    p_k = (v[w_price - 1:] - low) / (high - low)

    p_d = sma(p_k, w_k)
    p_d_slow = sma(p_d, w_d)

    return p_d, p_d_slow


def tr(ts: np.ndarray) -> np.ndarray:
    """ Calculates the True Range (TR) as the maximum between:
            1. abs(high_{t} - low_{t})
            2. abs(high_{t} - close_{t-1})
            3. abs(low_{t} - close_{t-1})
        The ts array is expected with shape (3, n) with structure:
            <high, low, close>.
        If an array with shape (n,) is provided, the TR is calculated as:
            |ts_{i} - ts_{i-1}|.

        Input:
            ts [np.ndarray]: input candles or prices

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
        raise ValueError("tr(): Input malformed: ts.shape != (n,) or (3, n)")


def tsi(ts: np.ndarray, w_fast: int, w_slow: int) -> np.ndarray:
    """ Calculates the True Strength Index over the given window. The ts array
        is expected with shape (3, n) with each row representing respectively
        high, low, close. If an array with shape (n,) is provided, the normal
        volatility is calculated as a backup solution.

        Input:
            ts [np.ndarray]: input return series
            w_fast [int]: short rolling window size
            w_slow [int]: long rolling window size

        Output:
            tsi [np.ndarray]: True Strength Index series
    """
    _check_len(ts, w_slow+w_fast)

    d = np.empty_like(ts)
    d[0] = np.nan
    d[1:] = ts[:-1] - ts[1:]
    fs = ewma(d, w_slow)
    pc = ewma(fs, w_fast)

    fs = ewma(np.abs(d), w_slow)
    apc = ewma(fs, w_fast)

    return 100. * (pc / apc)
