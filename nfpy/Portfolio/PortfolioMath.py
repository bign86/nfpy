#
# Portfolio math functions
# Creates/Deletes trades and updates positions
#

import numpy as np

from nfpy.Handlers.AssetFactory import get_af_glob
from nfpy.Handlers.Calendar import get_calendar_glob
from nfpy.Handlers.CurrencyFactory import get_fx_glob
from nfpy.Tools.TSUtils import ffill_cols, dropna


def portfolio_value(uids: list, ccy: str, pos: np.array) -> tuple:
    """ Get the value in the portfolio base currency of each position.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency
            pos [np.array]: array of positions over time

        Output:
            tot_value [np.array]: series of portfolio total values
            pos_value [np.array]: series of position values
    """
    # Collect prices
    af, fx = get_af_glob(), get_fx_glob()
    for i, u in enumerate(uids):
        if u == ccy:
            continue

        asset = af.get(u)
        p = asset.prices
        pos_ccy = asset.currency
        rate = 1.
        if pos_ccy != ccy:
            fx_obj = fx.get(pos_ccy, ccy)
            rate = fx_obj.prices.values

        pos[:, i] *= p.values * rate

    # Forward-fill values
    pos = ffill_cols(pos, .0)
    tot_val = np.sum(pos, axis=1)

    return tot_val, pos


def weights(uids: list, ccy: str, pos: np.array) -> tuple:
    """ Get the portfolio weights.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency
            pos [np.array]: array of positions over time

        Output:
            wgt [np.array]: weights array
    """
    tot_val, pos_val = portfolio_value(uids, ccy, pos)
    return pos_val / tot_val[:, None]


def price_returns(uids: list, ccy: str, pos: np.array = None,
                  wgt: np.array = None) -> np.array:
    """ Get the portfolio price returns.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency
            pos [np.array]: array of positions over time
            wgt [np.array]: array of weights over time

        Output:
            ret [np.array]: returns series
    """
    if not wgt and not pos:
        raise ValueError('Time series of positions required to calculate weights')
    elif not wgt:
        wgt = weights(uids, ccy, pos)

    af, fx = get_af_glob(), get_fx_glob()
    for i, u in enumerate(uids):
        if u == ccy:
            wgt[:, i] *= .0
            continue

        asset = af.get(u)
        r = asset.returns.values
        pos_ccy = asset.currency
        rate = .0
        if pos_ccy != ccy:
            fx_obj = fx.get(pos_ccy, ccy)
            rate = fx_obj.returns.values

        wgt[:, i] *= r + rate + r * rate

    return np.sum(wgt, axis=1)


def covariance(uids: list, ccy: str) -> np.array:
    """ Get the portfolio covariance.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency

        Output:
            ret [np.array]: returns series
            uids [Sequence]: ordered list of uids in the covariance matrix
    """
    af, fx = get_af_glob(), get_fx_glob()

    if ccy in uids:
        uids = list(uids)
        idx = uids.index(ccy)
        del uids[idx]

    n = len(get_calendar_glob())
    m = len(uids)
    ret = np.empty((m, n))

    for i, u in enumerate(uids):
        asset = af.get(u)
        r = asset.returns.values
        pos_ccy = asset.currency
        rate = .0
        if pos_ccy != ccy:
            fx_obj = fx.get(pos_ccy, ccy)
            rate = fx_obj.returns.values

        ret[i, :] = r + rate + r * rate

    ret, _ = dropna(ret, axis=0)
    return np.cov(ret), uids


def correlation(uids: list, ccy: str) -> np.array:
    """ Get the portfolio correlation.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency

        Output:
            ret [np.array]: returns series
            uids [Sequence]: ordered list of uids in the correlation matrix
    """
    af, fx = get_af_glob(), get_fx_glob()

    if ccy in uids:
        uids = list(uids)
        idx = uids.index(ccy)
        del uids[idx]

    n = len(get_calendar_glob())
    m = len(uids)
    ret = np.empty((m, n))

    for i, u in enumerate(uids):
        asset = af.get(u)
        r = asset.returns.values
        pos_ccy = asset.currency
        rate = .0
        if pos_ccy != ccy:
            fx_obj = fx.get(pos_ccy, ccy)
            rate = fx_obj.returns.values

        ret[i, :] = r + rate + r * rate

    ret, _ = dropna(ret, axis=0)
    return np.corrcoef(ret), uids
