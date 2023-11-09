#
# Building Blocks
# Functions and objects for equity valuation
#

from dataclasses import dataclass
import numpy as np
from typing import (Optional, Union)

from nfpy import Math
from nfpy.Assets import (get_af_glob, TyAsset)
from nfpy.Calendar import Frequency
from nfpy.Tools import (Constants as Cn, Exceptions as Ex)

from ..FinancialsFactory import get_fin_glob


@dataclass(eq=False, order=False, frozen=True)
class CAPMResult(object):
    uid: str
    market: str

    start: np.datetime64
    end: np.datetime64
    frequency: Frequency

    capm_return: Union[float, np.ndarray]
    mkt_return: Union[float, np.ndarray]
    beta: Union[float, np.ndarray]
    rf: Union[float, np.ndarray]


class CAPM(object):
    """ Calculates the CAPM model. """

    def __init__(self, eq: Union[str, TyAsset]):
        self._af = get_af_glob()
        self._rf = get_fin_glob()

        if isinstance(eq, str):
            eq = self._af.get(eq)

        if not eq.type == 'Equity':
            raise Ex.AssetTypeError(f'CAPM(): {eq.uid} is not an equity but a {eq.type}')

        self._eq = eq
        self._idx = self._af.get(self._eq.index)

    def calculate(self, start: Optional[np.datetime64] = None,
                  end: Optional[np.datetime64] = None) -> CAPMResult:

        # Get all relevant series
        return_series = self._eq.returns
        dt = return_series.index.to_numpy()
        returns = return_series.to_numpy()
        b_returns = self._idx.returns.to_numpy()

        # Get beta
        beta = Math.beta(
            dt, returns, b_returns,
            start=start, end=end
        )[1]

        # Get Market and RF returns
        mkt_return = Math.compound(
            self._idx.expct_return(start=start, end=end),
            Cn.BDAYS_IN_1Y
        )

        # Calculate the risk free
        rf = self._rf \
            .get_rf(self._eq.currency) \
            .last_price()[0]

        capm_ret = rf + beta*(mkt_return - rf)

        return CAPMResult(
            uid=self._eq.uid,
            market=self._idx.uid,
            start=start,
            end=end,
            frequency=Frequency.D,
            capm_return=capm_ret,
            mkt_return=mkt_return,
            beta=beta,
            rf=rf
        )
