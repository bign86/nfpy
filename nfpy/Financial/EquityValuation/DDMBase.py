#
# DDM Base
# Parent class for DDM models.
#

from abc import abstractmethod
import numpy as np
import pandas as pd

import nfpy.Financial as Fin
from nfpy.Math import (last_valid_value, next_valid_value)
from nfpy.Tools import (Constants as Cn, Exceptions as Ex)

from .BaseFundamentalModel import (BaseFundamentalModel, FundamentalModelResult)


class DDMResult(FundamentalModelResult):
    """ Object containing the results of the Discounted Dividend Model family. """


class DDMBase(BaseFundamentalModel):
    _RES_OBJ = DDMResult

    def __init__(self, uid: str, **kwargs):
        super().__init__(uid)

        self._df = Fin.DividendFactory(self._eq)
        self._rf = Fin.get_rf_glob()

        self._lt_div_w = kwargs.get('lt_div_w', 7)
        self._st_div_w = kwargs.get('st_div_w', 3)
        self._growth_weight = kwargs.get('growth_weight', .7)
        self._gdp_w = kwargs.get('gdp_w', 20)
        self._infl_w = kwargs.get('infl_w', 20)

        self._st_growth = None
        self._lt_growth = None
        self._inflation = None
        # self._macro_ke = None

        self._cf_no_gwt = None
        self._cf_gwt = None
        self._div_ts = None
        self._dt = None
        self._last_price = None
        self._rates = None

        self._check_applicability()

    def _calc_freq(self) -> None:
        """ Calculates model frequency. """
        self._freq = self._df.frequency

    def _calc_macro_variables(self) -> None:
        """ Returns the last price of the company's equity converted in the
            same currency as the company for consistency with the reported
            financial statements figures.
        """
        # Get last price
        # v, dt, _ = self._eq.last_price()
        # cv_obj = Ast.get_fx_glob() \
        #     .get(self._eq.currency, self._comp.currency)
        # self._last_price = v  # * cv_obj.get(dt)
        self._last_price = self._eq.last_price()[0]

        # Get dividends drift as the drift of the net income
        ff = Fin.FundamentalsFactory(self._comp)
        try:
            _, eq = ff.total_equity('A')
            _, ni = ff.net_income('A')
            _, so = ff.common_shares('A')
            ni_ps = ni / so
            eq_ps = eq / so

            d0 = self._df.dividends[1][-1]
            growths = (ni_ps - d0) / eq_ps

            annual_drift = np.nanmean(growths)
        except ValueError:
            annual_drift = .0
        # try:
        #     lt_drift = self._df.growth(self._lt_div_w)
        #     st_drift = self._df.growth(self._st_div_w)
        #     high = max(lt_drift, st_drift)
        #     low = min(lt_drift, st_drift)
        #     annual_drift = self._growth_weight * low \
        #                        + (1 - self._growth_weight) * high
        # except ValueError:
        #     annual_drift = .0

        # Get GDP and Inflation rates
        country = self._eq.country
        gdp_rate = self._rf \
            .get_gdp(country) \
            .prices.values
        self._inflation = self._rf \
            .get_inflation(country) \
            .prices.values

        # Long term macro
        idx_macro = self._gdp_w - 1
        lt_gdp = np.nanmean(gdp_rate[-idx_macro:])
        idx_infl = (self._infl_w - 1) * 12
        lt_infl = np.nanmean(
            self._inflation[-idx_infl:]
        )

        # Short term macro
        # idx_macro = self._st_macro_years - 1
        # st_gdp = np.nanmean(gdp_rate[-idx_macro:])
        # idx_infl = idx_macro * 12
        # st_infl = np.nanmean(
        #     inflation_rate[-idx_infl:]
        # )
        # self._macro_ke = st_gdp + st_infl

        # Short term macro
        self._st_growth = annual_drift
        self._lt_growth = min(
            annual_drift,
            lt_gdp + lt_infl
        )

        # Calculate the series for plotting
        divs = self._df.dividends
        self._div_ts = pd.Series(divs[1], index=divs[0])

    @abstractmethod
    def _calc_fv(self, den: float, dr: float) -> tuple:
        pass

    def _check_applicability(self) -> None:
        """ Check applicability of the DDM model to the equity. The presence
            and frequency of dividends is checked.
        """
        # We assume DDM cannot be used if dividends are NOT paid
        if not self._df.is_dividend_payer:
            raise Ex.MissingData(f'No dividends for {self._eq.uid}')

        # If the last dividend was outside the tolerance for the inferred
        # frequency, assume the dividend has been suspended
        if self._df.is_dividend_suspended:
            msg = f'Dividends for {self._uid} [{self._eq.uid}] appear to have been suspended'
            raise Ex.MissingData(msg)

    def _otf_calculate(self, **kwargs) -> dict:
        """ Calculate equity cost and denominator for the perpetual dividend.
            In input give the annual required rate of return. If not supplied,
            the equity cost is calculated as:
                dr = yield + drift - yield_gvt
        """

        dr = kwargs.get('d_rate', None)
        if dr is None:
            dr, _ = last_valid_value(self._inflation)
        #     dr = self._df.div_yield(Cn.BDAYS_IN_1M) + self._macro_ke
        #     try:
        #         rf = Fin.get_rf_glob() \
        #             .get_rf(self._comp.country) \
        #             .last_price()[0]
        #     except Ex.MissingData:
        #         rf = .0
        #
        #     # dr = D_yield + g_LT - G_yield
        #     dr -= rf

        # Calculate denominator and check model consistency
        den = dr - self._lt_growth
        if den <= 0.:
            msg = f'Ke={dr:.1%} < g={self._lt_growth:.1%} for {self._uid}'
            raise ValueError(msg)

        fv_no_gwt, fv_gwt, ret_no_gwt, ret_gwt = self._calc_fv(den, dr)
        return {
            'uid': self._uid,
            'ccy': self._eq.currency,
            'equity': self._eq.uid,
            'last_price': self._last_price,
            'd_rate': dr,
            'div_ts': self._div_ts,

            'dates': self._dt,
            'rates': self._rates,
            'fv_growth': fv_gwt,
            'fv_no_growth': fv_no_gwt,
            'ret_growth': ret_gwt,
            'ret_no_growth': ret_no_gwt,
            'div_growth': self._cf_gwt,
            'div_no_growth': self._cf_no_gwt,
        }
