#
# Utilities
# Functions for indicator functions and classes.
#

import numpy as np

from nfpy.Tools import Exceptions as Ex


def _check_len(v, w) -> None:
    l = v.shape[len(v.shape) - 1]
    if l < w:
        raise Ex.ShortSeriesError(f'The provided Series is too short {l} < {w}')


# TODO: expand to 2D
def _check_nans(v: np.ndarray) -> None:
    if np.sum(np.isnan(v), axis=0) > 0:
        raise Ex.NanPresent(f'The provided Series contains NaNs')
