#
# Equity class
# Base class for simple equity stock
#

import pandas as pd

import nfpy.Financial.Math as Math
from nfpy.Tools import (Exceptions as Ex)

from .Asset import Asset
from .AssetFactory import get_af_glob


class Equity(Asset):
    """ Base class for equities """

    _TYPE = 'Equity'
    _BASE_TABLE = 'Equity'
    _TS_TABLE = 'EquityTS'
    _TS_ROLL_KEY_LIST = ['date']

    def __init__(self, uid: str):
        super().__init__(uid)
        self._index = None
        self._div = None
        self._div_special = None
        self._split = None

    @property
    def index(self) -> str:
        return self._index

    @index.setter
    def index(self, v: str):
        self._index = v

    @property
    # TODO: dividends are not adjusted for splits in the current implementation
    def dividends(self) -> pd.Series:
        """ Loads the regular dividends series for the equity. The dividends are
            first converted in the base currency.
        """
        if self._div is None:
            try:
                res = self.load_dtype('dividend')['dividend']
            except Ex.MissingData:
                res = pd.Series()
            self._div = res
        return self._div

    @property
    # TODO: dividends are not adjusted for splits in the current implementation
    def dividends_special(self) -> pd.Series:
        """ Loads the special dividends series for the equity. The dividends are
            first converted in the base currency.
        """
        if self._div_special is None:
            try:
                res = self.load_dtype('dividendSpecial')
            except Ex.MissingData:
                res = pd.Series()
            self._div_special = res
        return self._div_special

    @property
    def splits(self) -> pd.Series:
        """ Loads the splits series for the equity. """
        if self._split is None:
            try:
                res = self.load_dtype('split')
            except Ex.MissingData:
                res = pd.Series()
            self._split = res
        return self._split

    @property
    def adjusting_factors(self) -> pd.Series:
        """ Returns the series of adjusting factors for splits and dividends. """
        try:
            adj_f = self._df['adj_factors']
        except KeyError:
            # FIXME: splits are not present since Yahoo does the adjustment for splits
            self._adjust_prices()
            adj_f = self._df['adj_factors']
        return adj_f

    # TODO: splits are not considered in the current implementation
    @property
    def prices(self) -> pd.Series:
        """ Returns the series of prices adjusted for dividends. """
        try:
            adj_p = self._df['adj_price']
        except KeyError:
            self._adjust_prices()
            adj_p = self._df['adj_price']
        return adj_p

    @property
    def raw_prices(self) -> pd.Series:
        """ Loads the raw price series for the equity. """
        try:
            res = self._df["price"]
        except KeyError:
            self.load_dtype_in_df("price")
            res = self._df["price"]
        return res

    def _adjust_prices(self):
        div = self.dividends
        rp = self.raw_prices
        adj_p, adj_f = rp, 1.

        # If the equity does pay dividends calculate adj_factors
        if div is not None:
            adj_f = Math.adj_factors(rp.values, rp.index.values,
                                     div.values, div.index.values)
            adj_p = adj_f * rp

        self._df['adj_price'] = adj_p
        self._df['adj_factors'] = adj_f

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
                adj_beta [Union[float, pd.Series]]: adjusted beta
                intercept [Union[float, pd.Series]]: intercept of the regression
        """
        if benchmark is None:
            benchmark = get_af_glob().get(self.index)
        elif not isinstance(benchmark, Asset):
            raise TypeError('Wrong benchmark type')

        eq = self.log_returns if log else self.returns
        idx = benchmark.log_returns if log else benchmark.returns
        start_dt = start.asm8 if start else None
        end_dt = end.asm8 if end else None
        return Math.beta(eq.index.values, eq.values, idx.values,
                         start_dt, end_dt, w)

    def correlation(self, benchmark: Asset = None, start: pd.Timestamp = None,
                    end: pd.Timestamp = None, w: int = None, log: bool = False) \
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
        start_dt = start.asm8 if start else None
        end_dt = end.asm8 if end else None
        return Math.correlation(eq.index.values, eq.values, idx.values,
                                start_dt, end_dt, w)
