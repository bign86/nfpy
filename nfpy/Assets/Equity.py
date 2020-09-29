#
# Equity class
# Base class for simple equity stock
#

import pandas as pd

from nfpy.Assets.Asset import Asset
from nfpy.Financial.TSMath import adjust_series, beta
from nfpy.Tools.TSUtils import ts_yield
from nfpy.Handlers.AssetFactory import get_af_glob


class Equity(Asset):
    """ Base class for equities """

    _TYPE = 'Equity'
    _BASE_TABLE = 'Equity'
    _TS_TABLE = 'EquityTS'
    _TS_ROLL_KEY_LIST = ['date']

    def __init__(self, uid: str):
        super().__init__(uid)
        # self._index = None
        # self._company_uid = None

    # @property
    # def index(self) -> str:
    #     return self._index
    #
    # @index.setter
    # def index(self, v: str):
    #     self._index = v

    @property
    def dividends(self) -> pd.Series:
        """ Loads the dividends series for the equity. The dividends are first 
            converted in the base currency.
        """
        try:
            res = self._df['dividend']
        except KeyError:
            self.load_dtype('dividend')
            # if self._df['dividend'].count() > 0:
            #     obj_fx = self._fx.get(self.currency)
            #     self._df['dividend'] = self._df['dividend'] * obj_fx.prices
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
            fc = self._df['adj_factors']
        except KeyError:
            # FIXME: splits are not present since Yahoo does the adjustment for splits
            adjp, fc = adjust_series(self.prices, None, [self.dividends])
            self._df['adj_price'] = adjp
            self._df['adj_factors'] = fc
        return fc

    @property
    def adjusted_prices(self) -> pd.Series:
        """ Returns the series of prices adjusted for splits and dividends. """
        try:
            adjp = self._df['adj_price']
        except KeyError:
            # FIXME: splits are not present since Yahoo does the adjustment for splits
            adjp, fc = adjust_series(self.prices, None, [self.dividends])
            self._df['adj_price'] = adjp
            self._df['adj_factors'] = fc
        return adjp

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
                beta [Union[float, pd.Series]]: beta of the regression
                intercpt [Union[float, pd.Series]]: intercept of the regression
                std_err [Union[float, pd.Series]]: error of the regression
        """
        # if not self._is_loaded:
        #     self.load()
        if benchmark is None:
            benchmark = get_af_glob().get(self.index)
        elif not isinstance(benchmark, Asset):
            raise TypeError('Wrong benchmark type')

        eq = self.log_returns if log else self.returns
        idx = benchmark.log_returns if log else benchmark.returns
        return beta(eq, idx, start, end, w)

    def div_yield(self, date: pd.Timestamp = None):
        div, p = self.dividends, self.prices
        div_ts, div_dt = div.values, div.index.values
        p_ts, p_dt = p.values, p.index.values
        return ts_yield(div_ts, div_dt, p_ts, p_dt, date)
