#
# Portfolio math functions
# Creates/Deletes trades and updates positions
#

import numpy as np

from nfpy.Assets import get_af_glob
from nfpy.Handlers.Calendar import get_calendar_glob
from nfpy.Handlers.CurrencyFactory import get_fx_glob
from nfpy.Tools.TSUtils import ffill_cols, dropna, trim_ts


def portfolio_value(uids: list, ccy: str, dt: np.ndarray, pos: np.ndarray) -> tuple:
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
            p = asset.prices
            asset_ccy = asset.currency
            rate = 1.
            if asset_ccy != ccy:
                fx_obj = fx.get(asset_ccy, ccy)
                rate = fx_obj.prices.values
            value = p.values * rate

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
    dt, tot_val, pos_val = portfolio_value(uids, ccy, dt, pos)
    wgt = pos_val / tot_val[:, None]
    return dt, wgt


def price_returns(uids: list, ccy: str, dt_pos: np.ndarray = None,
                  pos: np.ndarray = None, dt_wgt: np.ndarray = None,
                  wgt: np.ndarray = None) -> tuple:
    """ Get the portfolio price returns.

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
    if (wgt is None) and (pos is None):
        raise ValueError('Time series of positions required to calculate weights')
    elif wgt is None:
        dt_wgt, wgt = weights(uids, ccy, dt_pos, pos)

    af, fx = get_af_glob(), get_fx_glob()
    ret = np.empty((len(dt_wgt), len(uids)))
    for i, u in enumerate(uids):
        if u == ccy:
            ret[:, i] = .0
            continue

        asset = af.get(u)
        r = asset.returns.values
        pos_ccy = asset.currency
        rate = .0
        if pos_ccy != ccy:
            fx_obj = fx.get(pos_ccy, ccy)
            rate = fx_obj.returns.values

        ret[:, i] = r + rate + r * rate

    ret *= wgt
    return dt_wgt, np.sum(ret, axis=1)


def covariance(uids: list, ccy: str) -> tuple:
    """ Get the portfolio covariance.

        Input:
            uids [Sequence]: list of uids in the position array
            ccy [str]: base currency

        Output:
            ret [np.ndarray]: returns series
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


# Correlation exists also in EquityMath for two series.
def correlation(uids: list, ccy: str) -> tuple:
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
