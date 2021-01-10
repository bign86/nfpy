#
# Market Assets Data Base Model
# Base class for market models
#

import pandas as pd
from typing import Union

from .MarketAssetsDataBaseModel import (BaseMADMResult,
                                        MarketAssetsDataBaseModel)


class MPDMResult(BaseMADMResult):
    """ Base object containing the results of the market portfolio models. """


class MarketPortfolioDataModel(MarketAssetsDataBaseModel):
    """ Market Portfolio Data Model class """

    _RES_OBJ = MPDMResult

    def _calculate(self):
        super()._calculate()

        uids = self._asset.constituents_uids
        weights = self._asset.weights.values[-1]
        constituents = pd.DataFrame(weights, index=uids, columns=['Weights'])

        self._res_update(constituents=constituents)


def MPDModel(uid: str, date: Union[str, pd.Timestamp] = None,
             w_ma_slow: int = 120, w_ma_fast: int = 21, sr_mult: float = 5.,
             date_fmt: str = '%Y-%m-%d') -> MPDMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return MarketPortfolioDataModel(uid, date, w_ma_slow, w_ma_fast, sr_mult,
                                    date_fmt).result()
