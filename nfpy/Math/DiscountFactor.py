#
# Discount Factor functions
# Function and main class to calculate discount factors
#

import numpy as np
from scipy.interpolate import splrep, splev
from typing import (Optional, Union)

from .Returns_ import compound


def df(r: float, t: int, n: int = 1, mode: str = 'simple') -> float:
    """ General function for discount factors. Choose the type of discount in
        mode among
            - simple: sdf(r, t)
            - compound: cdf(r, t, n)
            - continue: ccdf(r, t)
    """
    modes = {'simple': cdf, 'continue': ccdf}
    return modes[mode](r, t, n)


def cdf(r: float, t: int, n: int = 1) -> float:
    """ Annually compounded discount factor D for a zero-rate r over the time t
        in years over n periods per years
            $D = \frac{1}{(1 + \frac{r}{n})^{n t}}$
    """
    return 1./(1. + compound(r, t, n))


def ccdf(r: float, t: int) -> float:
    """ Continuously compounded discount factor D for a zero-rate r over the
        time t in years
            $D = \exp{-r t}$
    """
    return np.exp(-(1. + r) * t)


def dcf(cf: np.ndarray, r: Union[float, np.ndarray],
        interpolate: Optional[np.ndarray] = None, n: int = 1) -> np.ndarray:
    """ Discounted cash flow. Cash flow must contain the terminal or repaying value.
        
        Input:
            cf [np.ndarray]: 2D data (periods, value) of cash flows
            r [Union[float, np.ndarray]]: if float is the rate corresponding to
                the yield to maturity. If np.ndarray calculates from the term
                structure
            interpolate [Optional[np.ndarray]]: array of tenors at which to
                interpolate the supplied rate term structure
            n [int]: frequency of compounding
        
        Output:
            dcf [np.ndarray]: Discounted cash flows
    """
    # FIXME: adjust the handling of input parameters. We can pass the term
    #        structure as an 2D-array as for cf and avoid the use of 't'
    if isinstance(r, np.ndarray):
        # FIXME: a ndarray is returned, we need only rates not tenors
        r = rate_interpolate(r, cf[0, :], interpolate)

    comp = compound(r, cf[0, :], n) + 1.
    return cf[1, :] / comp


# TODO: move into the Rate Factory or in another more appropriate place
def rate_interpolate(r: np.ndarray, tenors: np.ndarray,
                     interpolate: Union[float, np.ndarray],
                     method: str = 'spline') \
        -> np.ndarray:
    """ Interpolate """
    if method == 'spline':
        m = tenors.shape[0] * .3
        spl = splrep(tenors, r, k=3, s=m)
        r_intp = splev(interpolate, spl)
    else:
        raise ValueError(f'rate_interpolate method {method} not recognized')

    return r_intp
