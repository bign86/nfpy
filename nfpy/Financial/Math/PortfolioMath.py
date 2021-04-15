#
# Portfolio math functions
# Creates/Deletes trades and updates positions
#

import numpy as np
from typing import Sequence

from nfpy.Assets import get_af_glob
from nfpy.Calendar import get_calendar_glob

from .TSUtils import (dropna, ffill_cols, trim_ts)
from ..Currency import get_fx_glob


def ptf_value(uids: list, ccy: str, dt: np.ndarray, pos: np.ndarray) -> tuple:
    """ Get the value in the portfolio base currency of each position.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency
            dt [np.ndarray]: array of position dates
            pos [np.ndarray]: array of positions over time

        Output:
            dt [np.ndarray]: array of total value dates
            tot_value [np.ndarray]: series of portfolio total values
            pos_value [np.ndarray]: series of position values
    """
    af, fx = get_af_glob(), get_fx_glob()
    cal = get_calendar_glob()

    # The -1 takes into account the presence of the base currency
    pos, dt = trim_ts(pos, dt, start=cal.start.asm8, end=cal.end.asm8)

    for i, u in enumerate(uids):
        if u == ccy:
            continue

        elif fx.is_ccy(u):
            asset = fx.get(u, ccy)
            value = asset.prices

        else:
            asset = af.get(u)
            value = np.copy(asset.prices.values)
            asset_ccy = asset.currency
            if asset_ccy != ccy:
                fx_obj = fx.get(asset_ccy, ccy)
                value *= fx_obj.prices.values

        pos[:, i] *= value

    # Forward-fill values
    pos = ffill_cols(pos, .0)
    tot_val = np.sum(pos, axis=1)

    return dt, tot_val, pos


def weights(uids: list, ccy: str, dt: np.ndarray, pos: np.ndarray) -> tuple:
    """ Get the portfolio weights.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency
            dt [np.ndarray]: array of position dates
            pos [np.ndarray]: array of positions over time

        Output:
            dt [np.ndarray]: array of weight dates
            wgt [np.ndarray]: weights array
    """
    dt, tot_val, pos_val = ptf_value(uids, ccy, dt, pos)
    wgt = pos_val / tot_val[:, None]
    return dt, wgt


def price_returns(uids: list, ccy: str, dt_pos: np.ndarray = None,
                  pos: np.ndarray = None, dt_wgt: np.ndarray = None,
                  wgt: np.ndarray = None) -> tuple:
    """ Get the portfolio price returns by consolidating constituents returns
        and adjusting for the currency.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency
            dt_pos [np.ndarray]: array of position dates
            pos [np.ndarray]: array of positions over time
            dt_wgt [np.ndarray]: array of weight dates
            wgt [np.ndarray]: array of weights over time

        Output:
            dt [np.ndarray]: array of return dates
            ret [np.ndarray]: returns series
    """
    if wgt is None:
        if pos is None:
            raise ValueError('Time series of positions required to calculate weights')
        dt_wgt, wgt = weights(uids, ccy, dt_pos, pos)

    m = len(uids)
    n = len(dt_wgt)
    ret = _ret_matrix((m, n), uids, ccy)
    ret *= wgt.T

    return dt_wgt, np.sum(ret, axis=0)


def ptf_cov(uids: list, ccy: str) -> tuple:
    """ Get the portfolio covariance.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency

        Output:
            ret [np.ndarray]: returns series
            uids [Sequence]: ordered list of uids in the covariance matrix
    """
    uids = list(uids)
    try:
        uids.remove(ccy)
    except ValueError:
        pass

    m = len(uids)
    n = len(get_calendar_glob())
    ret = _ret_matrix((m, n), uids, ccy)
    ret, _ = dropna(ret, axis=0)

    return np.cov(ret), uids


# Correlation exists also in EquityMath for two series.
def ptf_corr(uids: list, ccy: str) -> tuple:
    """ Get the portfolio correlation.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency

        Output:
            ret [np.array]: returns series
            uids [Sequence]: ordered list of uids in the correlation matrix
    """
    uids = list(uids)
    try:
        uids.remove(ccy)
    except ValueError:
        pass

    m = len(uids)
    n = len(get_calendar_glob())
    ret = _ret_matrix((m, n), uids, ccy)
    ret, _ = dropna(ret, axis=0)

    return np.corrcoef(ret), uids


def _ret_matrix(shape: tuple, uids: Sequence, ccy: str) -> np.ndarray:
    af, fx = get_af_glob(), get_fx_glob()
    ret = np.empty(shape)

    for i, u in enumerate(uids):
        if u == ccy:
            r = .0

        elif fx.is_ccy(u):
            asset = fx.get(u, ccy)
            r = np.copy(asset.returns.values)

        else:
            asset = af.get(u)
            r = np.copy(asset.returns.values)
            pos_ccy = asset.currency
            if pos_ccy != ccy:
                fx_obj = fx.get(pos_ccy, ccy)
                rate = fx_obj.returns.values
                r += (1. + r) * rate

        ret[i, :] = r

    return ret
