
from abc import abstractmethod
import numpy as np

# import nfpy.Assets as Ast
import nfpy.Financial as Fin
from nfpy.Tools import Exceptions as Ex

from .BaseFundamentalModel import (BaseFundamentalModel, FundamentalModelResult)


class DDMResult(FundamentalModelResult):
    """ Object containing the results of the Discounted Dividend Model family. """


class DDMBase(BaseFundamentalModel):

    _RES_OBJ = DDMResult

    def __init__(self, uid: str, **kwargs):
        super().__init__(uid)

        self._df = Fin.DividendFactory(self._eq)
        self._rf = Fin.get_rf_glob()

        self._cf_no_gwt = None
        self._cf_gwt = None
        self._div_ts = None
        self._last_price = None

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
        v, dt, _ = self._eq.last_price()
        # cv_obj = Ast.get_fx_glob() \
        #     .get(self._eq.currency, self._comp.currency)
        self._last_price = v  # * cv_obj.get(dt)

        # Get dividends drift
        try:
            div_drift_annual = self._df.annualized_drift
        except ValueError:
            div_drift_annual = .0

        # Get GDP and Inflation rates
        country = self._eq.country
        gdp_rate = self._rf \
            .get_gdp(country) \
            .prices.values
        gdp = np.nanmean(gdp_rate[-6:])
        inflation_rate = self._rf \
            .get_inflation(country) \
            .prices.values
        inflation = np.nanmean(inflation_rate[-13:])

        self._macro_drift = gdp + inflation

        self._st_div_drift = div_drift_annual
        self._lt_div_drift = min(
            div_drift_annual,
            self._macro_drift
        )

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
            dr = self._df.ttm_yield() + self._lt_div_drift
            try:
                rf = Fin.get_rf_glob() \
                    .get_rf(self._comp.country) \
                    .last_price()[0]
            except Ex.MissingData:
                rf = .0

            # dr = D_yield + g_LT - G_yield
            dr -= rf

        # Calculate denominator and check model consistency
        den = dr - self._lt_div_drift
        if den <= 0.:
            msg = f'Re={dr:.1%} < g={self._lt_div_drift:.1%} for {self._uid}'
            raise ValueError(msg)

        # print(f'ttm_yield + div_drift - rf = dr')
        # print(f'{self._df.ttm_yield():.1%} + {self._div_drift:.1%} - {rf:.1%} = {dr:.1%}')

        fv_no_gwt, fv_gwt, ret_no_gwt, ret_gwt = self._calc_fv(den, dr)

        return {
            'uid': self._uid,
            'ccy': self._eq.currency,
            'equity': self._eq.uid,
            'last_price': self._last_price,
            'd_rate': dr,
            'div_ts': self._div_ts,

            'short_term_drift': self._st_div_drift,
            'long_term_drift': self._lt_div_drift,
            'fv_no_growth': fv_no_gwt,
            'fv_growth': fv_gwt,
            'ret_no_growth': ret_no_gwt,
            'ret_growth': ret_gwt,
            'div_no_growth': self._cf_no_gwt,
            'div_growth': self._cf_gwt,
        }
