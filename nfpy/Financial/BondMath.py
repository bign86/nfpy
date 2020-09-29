#
# Bond math functions
# Functions with bond math
#

import numpy as np
from scipy.optimize import newton
from nfpy.Financial.DiscountFactor import dcf
from nfpy.Financial.TSMath import fv


def ytm(cf: np.ndarray, p0: float, accrued: float = .0) -> float:
    """ Calculated the YTM using the values from the cash flow dataframe as
        a numpy array for speed and reliability.
    """

    def _min_ytm(r, dt):
        return fv(dt, r, None, accrued) - p0

    return newton(_min_ytm, .02, args=(cf,))


def __time_cf(cf: np.ndarray, p0: float, accrued: float, exp: float) -> float:
    _ytm = ytm(cf, p0, accrued)
    wflow = dcf(cf, _ytm) * (cf[:, 0] ** exp)
    return float(wflow.sum()) / p0


def duration(cf: np.ndarray, p0: float, accrued: float = .0) -> float:
    """ Bond duration.

        Input:
            cf [np.ndarray]: data (periods, value) of cash flows
            p0 [float]: market price at t0
            accrued [float]: accrued interest to subtract from dirty price

        Output:
            _r [float]: duration
    """
    return __time_cf(cf, p0, accrued, 1.)


def convexity(cf: np.ndarray, p0: float, accrued: float = .0) -> float:
    """ Bond convexity.

        Input:
            cf [np.ndarray]: dataframe (periods, value) of cash flows
            p0 [float]: market price at t0
            accrued [float]: accrued interest to subtract from dirty price

        Output:
            _r [float]: duration
    """
    return __time_cf(cf, p0, accrued, 2.)
