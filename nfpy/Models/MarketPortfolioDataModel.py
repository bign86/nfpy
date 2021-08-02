#
# Market Assets Data Base Model
# Base class for market models
#

import pandas as pd
from typing import Union

from .MarketAssetsDataBaseModel import (MADMResult, MarketAssetsDataBaseModel)


class MPDMResult(MADMResult):
    """ Base object containing the results of the market portfolio models. """


class MarketPortfolioDataModel(MarketAssetsDataBaseModel):
    """ Market Portfolio Data Model class """

    _RES_OBJ = MPDMResult

    def _calculate(self):
        super()._calculate()
        summary = self._asset.summary()

        merged = pd.merge(
            summary['constituents_data'],
            pd.DataFrame(
                self._asset.weights.values[-1],
                index=self._asset.constituents_uids,
                columns=['weights']
            ),
            left_on='uid',
            right_index=True
        )

        self._res_update(
            last_trade=summary['date'],
            tot_value=summary['tot_value'],
            currency=summary['currency'],
            cnsts_data=merged
        )


def MPDModel(uid: str, date: Union[str, pd.Timestamp] = None) -> MPDMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return MarketPortfolioDataModel(uid, date).result()
