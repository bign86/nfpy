#
# Strategies functions
# Functions to compute buy-sell signals
# The output is a list of buy/sell signals
#

import pandas as pd
import numpy as np

from . import Signals_pd as Sig


def _align_series_(v, w):
    v = v.dropna()
    w = w.dropna()

    first_date = max(v.index[0], w.index[0])
    last_date = min(v.index[-1], w.index[-1])
    v = v.loc[first_date:last_date]
    w = w.loc[first_date:last_date]

    return v, w


def sma_price_cross(v: pd.Series, w: int = 21, ma: pd.Series = None) -> tuple:
    """ Buy/Sell strategy. Generates a buy signal when the price crosses above
        the SMA and a sell signal when the price crosses below the SMA.
    """
    if ma is None:
        ma = Sig.sma(v, w)

    _sma = ma.dropna()

    cross = pd.Series(np.where(v > _sma, 1, 0), index=_sma.index)
    signals = cross.diff(1).dropna()
    signals = signals[signals != 0]
    return signals, ma


def two_sma_cross(v: pd.Series, fast: int = 21, slow: int = 120,
                  fast_ma: pd.Series = None, slow_ma: pd.Series = None
                  ) -> tuple:
    """ Strategy that uses the cross of a fast SMA with a slow SMA. """
    if fast_ma is None:
        fast_ma = Sig.sma(v, fast)
    if slow_ma is None:
        slow_ma = Sig.sma(v, slow)

    f_sma, s_sma = _align_series_(fast_ma, slow_ma)

    cross = pd.Series(np.where(f_sma > s_sma, 1, 0), index=f_sma.index)
    signals = cross.diff(1).dropna()
    signals = signals[signals != 0]
    return signals, fast_ma, slow_ma


def ema_price_cross(v: pd.Series, w: int = 25, ma: pd.Series = None) -> tuple:
    """ Strategy that uses the cross of an EMA with the price signal. """
    if ma is None:
        ma = Sig.ewma(v, w)

    _ema = ma.dropna()

    cross = pd.Series(np.where(v > _ema, 1, 0), index=_ema.index)
    signals = cross.diff(1).dropna()
    signals = signals[signals != 0]
    return signals, ma


def two_ema_cross(v: pd.Series, fast: int = 9, slow: int = 21,
                  fast_ma: pd.Series = None, slow_ma: pd.Series = None
                  ) -> tuple:
    """ Strategy that uses the cross of a fast EMA with a slow EMA. """
    if fast_ma is None:
        fast_ma = Sig.ewma(v, fast)
    if slow_ma is None:
        slow_ma = Sig.ewma(v, slow)

    f_ema, s_ema = _align_series_(fast_ma, slow_ma)

    cross = pd.Series(np.where(f_ema > s_ema, 1, 0), index=f_ema.index)
    signals = cross.diff(1).dropna()
    signals = signals[signals != 0]
    return signals, fast_ma, slow_ma


def momentum_swing(v: pd.Series, fast: int = 8, slow: int = 25,
                   trend: int = 200, ma_type: str = 'ewma',
                   fast_ma: pd.Series = None, slow_ma: pd.Series = None,
                   ) -> tuple:
    if ma_type == 'ewma':
        _crossf = two_ema_cross
        _smaf = Sig.ewma
    elif ma_type == 'sma':
        _crossf = two_sma_cross
        _smaf = Sig.sma
    else:
        raise ValueError('Moving average type {} not recognized'.format(ma_type))

    fast_sma, slow_sma, signals = _crossf(v, fast, slow, fast_ma, slow_ma)
    trend_sma = _smaf(v, trend)
    trend_sig = (v - trend_sma).loc[signals.index]

    idxnan = trend_sig[np.isnan(trend_sig)].index
    idx1 = signals[(signals > 0.) & (trend_sig > 0.)].index
    idx2 = signals[(signals < 0.) & (trend_sig < 0.)].index
    signals.drop(idxnan, inplace=True)
    signals.drop(idx1, inplace=True)
    signals.drop(idx2, inplace=True)

    last = None
    idxdrop = []
    for i, sig in signals.iteritems():
        if sig == last:
            idxdrop.append(i)
        last = sig
    signals.drop(idxdrop, inplace=True)

    return signals, fast_sma, slow_sma, trend_sma


def macd_swing(v: pd.Series, fast: int = 50, slow: int = 200,
               wmacd: int = 40) -> tuple:
    macd_line, signal_line, histogram, _, _ = Sig.macd(v, fast, slow, wmacd)

    m_line, s_line = _align_series_(macd_line, signal_line)

    cross = pd.Series(np.where(m_line > s_line, 1, 0), index=m_line.index)
    signals = cross.diff(1).dropna()
    signals = signals[signals != 0]
    trigger = s_line.loc[signals.index]

    idxnan = trigger[np.isnan(trigger)].index
    idx1 = signals[(signals > 0.) & (trigger > 0.)].index
    idx2 = signals[(signals < 0.) & (trigger < 0.)].index
    signals.drop(idxnan, inplace=True)
    signals.drop(idx1, inplace=True)
    signals.drop(idx2, inplace=True)

    last = None
    idxdrop = []
    for i, sig in signals.iteritems():
        if sig == last:
            idxdrop.append(i)
        last = sig
    signals.drop(idxdrop, inplace=True)

    return signals, macd_line, signal_line, histogram
