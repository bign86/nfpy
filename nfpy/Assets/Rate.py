#
# Equity class
# Base class for simple equity stock
#

import pandas as pd

from .Asset import Asset

_CALENDAR_TRANSFORM = {
    'D': 'C',
    'M': 'BMS',
    'Y': 'BAS-JAN',
}


class Rate(Asset):
    """ Base class for interest rates """

    _TYPE = 'Rate'
    _BASE_TABLE = 'Rate'
    _TS_TABLE = 'RateTS'
    _TS_ROLL_KEY_LIST = ['date']

    def __init__(self, uid: str):
        super(Rate, self).__init__(uid)
        self._freq = None

    @property
    def frequency(self) -> str:
        return self._freq

    @frequency.setter
    def frequency(self, v: str):
        self._freq = v

    @property
    def prices(self) -> pd.Series:
        try:
            res = self._df["price"]
        except KeyError:
            self.load_dtype_in_df("price")
            res = self._df["price"]
        return res

    def load_dtype_in_df(self, dt: str):
        freq = self._df.index.freqstr
        if freq != _CALENDAR_TRANSFORM[self._freq]:
            if self._freq == 'M':
                calendar = self._cal.monthly_calendar
            elif self._freq == 'Y':
                calendar = self._cal.yearly_calendar
            else:
                raise ValueError('Rate(): calendar frequency not recognized')
            self._df = pd.DataFrame(index=calendar)

        df = self.load_dtype(dt)
        df.index = df.index + 0*pd.offsets.BDay()

        self._df = self._df.merge(
            df,
            how='left',
            left_index=True,
            right_index=True
        )
        self._df.sort_index(inplace=True)

        if dt == 'price':
            # The value from the database is in annual percentage points
            self._df.loc[:, 'price'] *= .01
