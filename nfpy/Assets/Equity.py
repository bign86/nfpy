#
# Equity class
# Base class for simple equity stock
#

import pandas as pd

from nfpy.Assets.Asset import Asset
from nfpy.Financial.EquityMath import adj_factors, beta, correlation
from nfpy.Handlers.AssetFactory import get_af_glob


class Equity(Asset):
    """ Base class for equities """

    _TYPE = 'Equity'
    _BASE_TABLE = 'Equity'
    _TS_TABLE = 'EquityTS'
    _TS_ROLL_KEY_LIST = ['date']

    def __init__(self, uid: str):
        super().__init__(uid)
        self._index = None

    @property
    def index(self) -> str:
        return self._index

    @index.setter
    def index(self, v: str):
        self._index = v

    @property
    # TODO: dividends are not adjusted for splits in the current implementation
    def dividends(self) -> pd.Series:
        """ Loads the dividends series for the equity. The dividends are first 
            converted in the base currency.
        """
        try:
            res = self._df['dividend']
        except KeyError:
            self.load_dtype('dividend')
            res = self._df['dividend']
        return res

    @property
    def splits(self) -> pd.Series:
        """ Loads the splits series for the equity. """
        try:
            res = self._df['split']
        except KeyError:
            self.load_dtype('split')
            res = self._df['split']
        return res

    @property
    def adjusting_factors(self) -> pd.Series:
        """ Returns the series of adjusting factors for splits and dividends. """
        try:
            adj_fct = self._df['adj_factors']
        except KeyError:
            # FIXME: splits are not present since Yahoo does the adjustment for splits
            adj_fct = adj_factors(self.raw_prices.values, self.dividends.values)
            self._df['adj_price'] = adj_fct * self.raw_prices
            self._df['adj_factors'] = adj_fct
        return adj_fct

    @property
    # TODO: splits are not considered in the current implementation
    def prices(self) -> pd.Series:
        """ Returns the series of prices adjusted for dividends. """
        try:
            prices = self._df['adj_price']
        except KeyError:
            adj_fct = adj_factors(self.raw_prices.values, self.dividends.values)
            prices = adj_fct * self.raw_prices
            self._df['adj_price'] = prices
            self._df['adj_factors'] = adj_fct
        return prices

    @property
    def raw_prices(self) -> pd.Series:
        """ Loads the raw price series for the equity. """
        try:
            res = self._df["price"]
        except KeyError:
            self.load_dtype("price")
            res = self._df["price"]
        return res

    def beta(self, benchmark: Asset = None, start: pd.Timestamp = None,
             end: pd.Timestamp = None, w: int = None, log: bool = False) -> tuple:
        """ Returns the beta between the equity and the benchmark index given as
            input. If dates are specified, the beta is calculated on the resulting
            interval (end date excluded). If a window is given, beta is calculated
            rolling.

            Input:
                benchmark [Asset]: usually an index (default: reference index)
                start [pd.Timestamp]: start date of the series (default: None)
                end [pd.Timestamp]: end date of the series excluded (default: None)
                w [int]: window size for rolling calculation (default: None)
                is_log [bool]: it set to True use is_log returns (default: False)

            Output:
                dt [Union[float, pd.Series]]: dates of the regression (None if
                                              not rolling)
                beta [Union[float, pd.Series]]: beta of the regression
                intercept [Union[float, pd.Series]]: intercept of the regression
        """
        if benchmark is None:
            benchmark = get_af_glob().get(self.index)
        elif not isinstance(benchmark, Asset):
            raise TypeError('Wrong benchmark type')

        eq = self.log_returns if log else self.returns
        idx = benchmark.log_returns if log else benchmark.returns
        return beta(eq.index.values, eq.values, idx.values,
                    start.asm8, end.asm8, w)

    def correlation(self, benchmark: Asset = None, start: pd.Timestamp = None,
                    end: pd.Timestamp = None, w: int = None, log: bool = False)\
            -> tuple:
        """ Returns the beta between the equity and the benchmark index given as
            input. If dates are specified, the beta is calculated on the resulting
            interval (end date excluded). If a window is given, beta is calculated
            rolling.

            Input:
                benchmark [Asset]: usually an index (default: reference index)
                start [pd.Timestamp]: start date of the series (default: None)
                end [pd.Timestamp]: end date of the series excluded (default: None)
                w [int]: window size for rolling calculation (default: None)
                is_log [bool]: it set to True use is_log returns (default: False)

            Output:
                dt [Union[float, pd.Series]]: dates of the regression (None if
                                              not rolling)
                beta [Union[float, pd.Series]]: beta of the regression
                intercept [Union[float, pd.Series]]: intercept of the regression
        """
        if benchmark is None:
            benchmark = get_af_glob().get(self.index)
        elif not isinstance(benchmark, Asset):
            raise TypeError('Wrong benchmark type')

        eq = self.log_returns if log else self.returns
        idx = benchmark.log_returns if log else benchmark.returns
        return correlation(eq.index.values, eq.values, idx.values,
                           start.asm8, end.asm8, w)
