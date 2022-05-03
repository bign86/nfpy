#
# Equity class
# Base class for simple equity stock
#

import numpy as np
import pandas as pd
from typing import Optional

import nfpy.Calendar as Cal
import nfpy.Math as Math
from nfpy.Tools import (Exceptions as Ex)

from . import get_af_glob
from .Asset import (Asset, TyAsset)


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

    def _adjust_prices(self) -> None:
        div = self.dividends
        rp = self.raw_prices
        adj_p, adj_f = rp, 1.

        # If the equity does pay dividends calculate adj_factors
        if div is not None:
            adj_f = self.adj_factors(rp.values, rp.index.values,
                                     div.values, div.index.values)
            adj_p = adj_f * rp

        self._df['adj_price'] = adj_p
        self._df['adj_factors'] = adj_f

    @staticmethod
    def adj_factors(ts: np.ndarray, dt: np.ndarray, div: np.ndarray,
                    div_dt: np.ndarray) -> np.ndarray:
        """ Calculate the adjustment factors given a dividend series.

            Input:
                ts [np.ndarray]: price series to calculate the yield
                dt [np.ndarray]: price series date index
                div [np.ndarray]: dividend series
                div_dt [np.ndarray]: dividend series date index

            Output:
                adjfc [np.ndarray]: series of adjustment factors
        """
        adj = np.ones(ts.shape)

        # Calculate conversion factors
        idx = np.searchsorted(dt, div_dt)
        for n, i in enumerate(idx):
            try:
                v = Math.last_valid_index(ts, i)
            except ValueError:
                pass
            else:
                adj[i] -= div[n] / ts[v]

        cp = np.nancumprod(adj)
        return adj / cp * cp[-1]

    def beta(self, benchmark: Optional[TyAsset] = None,
             start: Optional[Cal.TyDate] = None,
             end: Optional[Cal.TyDate] = None,
             w: Optional[int] = None, is_log: bool = False) -> tuple:
        """ Returns the beta between the equity and the benchmark index given
            as input. If dates are specified, the beta is calculated on the
            resulting interval (end date excluded). If a window is given, beta
            is calculated rolling.

            Input:
                benchmark [TyAsset]: usually an index (default: reference index)
                start [TyDate]: start date of the series (default: None)
                end [TyDate]: end date of the series (default: None)
                w [int]: window size for rolling calculation (default: None)
                is_log [bool]: it set to True use is_log returns (default: False)

            Output:
                beta [pd.Series]: beta of the regression
                adj_beta [pd.Series]: adjusted beta
                intercept [pd.Series]: intercept of the regression
        """
        if benchmark is None:
            benchmark = get_af_glob().get(self.index)
        elif not isinstance(benchmark, Asset):
            ty = type(benchmark).__name__
            raise TypeError(f'Objects of type {ty} cannot be used as benchmarks')

        eq = self.log_returns if is_log else self.returns
        idx = benchmark.log_returns if is_log else benchmark.returns
        dts, beta, adj_b, itc = Math.beta(
            eq.index.values,
            eq.values,
            idx.values,
            start=Cal.pd_2_np64(start),
            end=Cal.pd_2_np64(end),
            w=w
        )
        return (
            pd.Series(beta, index=dts),
            pd.Series(adj_b, index=dts),
            pd.Series(itc, index=dts)
        )

    def correlation(self, benchmark: Optional[TyAsset] = None,
                    start: Optional[Cal.TyDate] = None,
                    end: Optional[Cal.TyDate] = None,
                    is_log: bool = False) -> float:
        """ Returns the correlation between the equity and the benchmark given
            as input. If dates are specified, the correlation is calculated on
            the resulting interval (end date excluded).

            Input:
                benchmark [TyAsset]: usually an index (default: reference index)
                start [TyDate]: start date of the series (default: None)
                end [TyDate]: end date of the series excluded (default: None)
                is_log [bool]: it set to True use is_log returns (default: False)

            Output:
                corcoeff [float]: correlation coefficient
        """
        if benchmark is None:
            benchmark = get_af_glob().get(self.index)
        elif not isinstance(benchmark, Asset):
            ty = type(benchmark).__name__
            raise TypeError(f'Objects of type {ty} cannot be used as benchmarks')

        eq = self.log_returns if is_log else self.returns
        idx = benchmark.log_returns if is_log else benchmark.returns
        return Math.correlation(
            eq.index.values,
            eq.values,
            idx.values,
            start=Cal.pd_2_np64(start),
            end=Cal.pd_2_np64(end),
        )[0, 1]
