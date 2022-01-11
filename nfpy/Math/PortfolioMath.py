#
# Portfolio math functions
# Creates/Deletes trades and updates positions
#

import numpy as np
from typing import Sequence

from nfpy.Assets import (get_af_glob, get_fx_glob)
from nfpy.Calendar import get_calendar_glob

from .TSUtils_ import (dropna, ffill_cols)


def ptf_value(uids: list, ccy: str, pos: np.ndarray) -> tuple:
    """ Get the value in the portfolio base currency of each position.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency uid
            pos [np.ndarray]: array of positions as <time, uid> (assumed having
                              the same length as the calendar)

        Output:
            tot_value [np.ndarray]: series of portfolio total values
            pos_value [np.ndarray]: series of position values
    """
    af, fx = get_af_glob(), get_fx_glob()
    # cal = get_calendar_glob()
    # pos, dt = trim_ts(pos, dt, start=cal.start.asm8, end=cal.end.asm8)
    # Copy the array to return position values
    pos = np.array(pos)

    for i, u in enumerate(uids):
        if u == ccy:
            continue

        elif fx.is_ccy(u):
            pos[:, i] *= fx.get(u, ccy).prices

        else:
            asset = af.get(u)
            pos[:, i] *= asset.prices.values
            asset_ccy = asset.currency
            if asset_ccy != ccy:
                fx_obj = fx.get(asset_ccy, ccy)
                # We multiply for the position internally to avoid the copy of
                # the prices outside of this if that would be required if prices
                # and FX where multiplied together before adjusting the position
                # values.
                pos[:, i] *= fx_obj.prices.values

    # Forward-fill values
    # TODO: verify this IS in-place
    pos = ffill_cols(pos, .0)
    tot_val = np.sum(pos, axis=1)

    return tot_val, pos


def weights(uids: list, ccy: str, pos: np.ndarray) -> tuple:
    """ Get the portfolio weights.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency
            pos [np.ndarray]: array of positions as <time, uid> (assumed having
                              the same length as the calendar)

        Output:
            wgt [np.ndarray]: weights array
    """
    tot_val, pos_val = ptf_value(uids, ccy, pos)
    return pos_val / tot_val[:, None]


def price_returns(uids: list, ccy: str, pos: np.ndarray = None,
                  wgt: np.ndarray = None) -> np.ndarray:
    """ Get the portfolio price returns by consolidating constituents returns
        and adjusting for the currency.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency
            pos [np.ndarray]: array of positions as <time, uid> (assumed having
                              the same length as the calendar)
            wgt [np.ndarray]: array of weights as <time, uid> (assumed having
                              the same length as the calendar)

        Output:
            ret [np.ndarray]: returns series
    """
    if wgt is None:
        if pos is None:
            raise ValueError('Time series of positions required to calculate weights')
        wgt = weights(uids, ccy, pos)

    ret = _ret_matrix(uids, ccy)
    return np.sum(ret * wgt.T, axis=0)


def ptf_cov(uids: list) -> np.ndarray:
    """ Get the portfolio covariance. The list of uids should NOT include the
        base currency.

        Input:
            uids [Sequence]: list of uids in the position array

        Output:
            ret [np.ndarray]: portfolio covariance
    """
    return np.cov(
        dropna(
            _ret_matrix(uids),
            axis=0
        )[0]
    )


# Correlation exists also in EquityMath for two series.
def ptf_corr(uids: list) -> np.ndarray:
    """ Get the portfolio correlation. The list of uids should NOT include the
        base currency.

        Input:
            uids [Sequence]: list of uids in the position array

        Output:
            ret [np.ndarray]: portfolio correlations
    """
    return np.corrcoef(
        dropna(
            _ret_matrix(uids),
            axis=0
        )[0]
    )


def _ret_matrix(uids: Sequence, ccy: str = None) -> np.ndarray:
    """ Helper function to create a matrix of returns as <uid, time>.
        It is assumed <time> spans the whole calendar. The base currency must
        be supplied to ensure the correct FX rates are used.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency

        Output:
            ret [np.ndarray]: matrix of returns
    """
    af, fx = get_af_glob(), get_fx_glob()
    m = len(uids)
    n = len(get_calendar_glob())
    ret = np.empty((m, n), dtype=float)

    for i, u in enumerate(uids):
        if fx.is_ccy(u):
            if u == ccy:
                r = .0
            else:
                r = fx.get(u, ccy).returns.values

        else:
            asset = af.get(u)
            r = asset.returns.values
            pos_ccy = asset.currency
            if pos_ccy != ccy:
                rate = fx.get(pos_ccy, ccy).returns.values
                r += (1. + r) * rate

        ret[i, :] = r

    return ret


def ptf_dividends(ptf):
    cnst = ptf.constituents

