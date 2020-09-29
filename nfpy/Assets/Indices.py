#
# Index class
# Class for indices
#

import pandas as pd
from nfpy.Assets.Asset import Asset


class Indices(Asset):
    """ Class for indices """

    _TYPE = 'Indices'
    _BASE_TABLE = 'Indices'
    _TS_TABLE = 'IndexTS'
    _TS_ROLL_KEY_LIST = ['date']

    @property
    def prices(self) -> pd.Series:
        try:
            res = self._df["price"]
        except KeyError:
            self.load_dtype("price")
            res = self._df["price"]
        return res
