#
# Utility functions
#

import numpy as np
from typing import Sequence

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
import nfpy.Tools.Exceptions as Ex


def _ret_matrix(uids: Sequence[str], tgt_ccy: str) -> np.ndarray:
    """ Helper function to create a matrix of returns as <uid, time>.
        It is assumed <time> spans the whole calendar. The base currency
        must be supplied to ensure the correct FX rates are used as returns
        are in the base currency.

        input:
            uids [list]: list of uids to construct the matrix
            tgt_ccy [str]: target currency all returns are transformed into

        Output:
            ret [np.ndarray]: matrix of returns
    """
    # Get globals
    af = Ast.get_af_glob()
    fx = Ast.get_fx_glob()

    m = len(uids)
    n = Cal.get_calendar_glob().__len__()
    ret = np.empty((m, n), dtype=float)

    for i, uid in enumerate(uids):
        try:
            asset = af.get(uid)

            r = af.get(uid) \
                .returns \
                .to_numpy()

            if asset.currency != tgt_ccy:
                r_fx = fx.get(asset.currency, tgt_ccy) \
                    .returns \
                    .to_numpy()
                r += (1. + r) * r_fx
        except Ex.MissingData:
            if uid == tgt_ccy:
                r = .0
            else:
                r = fx.get(uid, tgt_ccy) \
                    .returns \
                    .to_numpy()

        ret[i, :] = r

    return ret
