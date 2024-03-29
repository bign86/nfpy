#
# Equity Math
# Mathematical functions for equities
#

import numpy as np
from typing import (Optional, Union)

from .DiscountFactor import dcf


def fv(cf: np.ndarray, r: Union[float, np.ndarray],
       t: Optional[np.ndarray] = None, accrued: float = .0) -> float:
    """ Fair value from discounted cash flow that are calculated if not present.

        Input:
            cf [np.ndarray]: data (periods, value) of cash flows
            r [Union[float, np.ndarray]]: if float is the rate corresponding to
                the yield to maturity. If ndarray calculate from the term structure
            t [Optional[np.ndarray]]: array of tenors (default: None)
            accrued [float]: accrued interest to subtract from dirty price
                (default: .0)

        Output:
            _r [float]: fair value
    """
    _dcf = float(dcf(cf, r, t).sum())
    return _dcf - accrued
