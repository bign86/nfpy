#
# Currency class
# Class for currencies saved as change ratio against another currency
#

import pandas as pd
from nfpy.Assets.Asset import Asset


class Currency(Asset):
    """ Class for currencies """

    _TYPE = 'Currency'
    _BASE_TABLE = 'Currency'
    _TS_TABLE = 'CurrencyTS'
    _TS_ROLL_KEY_LIST = ['date']

    @property
    def prices(self) -> pd.Series:
        try:
            res = self._df["price"]
        except KeyError:
            self.load_dtype("price")
            # self._df["price"].ffill(inplace=True)
            res = self._df["price"]
        return res
