#
# Equity class
# Base class for simple equity stock
#

import pandas as pd

from .Asset import Asset
from nfpy.Tools import Constants as Cn


class Rate(Asset):
    """ Base class for interest rates """

    _TYPE = 'Rate'
    _BASE_TABLE = 'Rate'
    _TS_TABLE = 'RateTS'
    _TS_ROLL_KEY_LIST = ['date']

    @property
    def prices(self) -> pd.Series:
        try:
            res = self._df["price"]
        except KeyError:
            self.load_dtype("price")
            res = self._df["price"]
        return res

    def load_dtype(self, dt: str):
        super().load_dtype(dt)

        if dt == 'price':
            # The value from the database is in annual percentage points
            self._df.loc[:, 'price'] *= .01/Cn.BDAYS_IN_1Y
