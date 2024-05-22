#
# Portfolio optimization engine
# Performs optimization of portfolios
#

import cutils
from typing import (Any, Sequence)

from .Optimizer import OptimizerResult
from .Utils import _ret_matrix

from nfpy.Tools import Utilities as Ut


def optimize_portfolio(
        method: str,
        parameters: dict[str, Any],
        uids: Sequence[str],
        tgt_ccy: str,
        dates_slice: slice | None = None,
        labels: Sequence[str] | None = None
) -> OptimizerResult:
    """ Prepare the data for optimizers and launch a portfolio optimization.

        Input:
            method [str]: indicated which optimization we want
            parameters [dict[str, Any]]: parameters to use for the
                optimization
            uids [Iterable[str]]: list of uids to use (not necessarily they
                should be in the portfolio)
            dates_slice [Optional[slice]]: slice of the calendar
            labels [Optional[Sequence[str]]]: labels to use in place of the uids
                in the output, must be of the same size as <uids>
    """
    if labels is not None:
        if len(uids) != len(labels):
            raise ValueError(f'Optimization(): uids and labels must have the same size')
    else:
        labels = uids

    ret_matrix = _ret_matrix(uids, tgt_ccy)
    if dates_slice:
        ret_matrix = ret_matrix[:, dates_slice]
    returns = cutils.dropna(ret_matrix, 1)

    # Create the optimizer object
    symbol = '.'.join(['nfpy.Financial.Portfolio.Optimizer', method, method])
    class_ = Ut.import_symbol(symbol)
    obj = class_(
        returns, 'B', labels,
        **parameters
    )

    # Run the optimizations
    return obj.result
