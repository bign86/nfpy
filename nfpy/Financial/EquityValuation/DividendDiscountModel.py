#
# Dividend Discount Model
# Class to calculate a stock fair value using the DDM
#

import numpy as np
import pandas as pd
from typing import Optional

import nfpy.Financial as Fin
import nfpy.Math as Math
from nfpy.Tools import Exceptions as Ex

from .DDMBase import (DDMBase, DDMResult)


class DividendDiscountModel(DDMBase):
    """ Dividend Discount Model class. """

    def __init__(self, uid: str, projection: int, **kwargs):
        super().__init__(uid)

        self._fp = projection

    def _get_future_dates(self) -> tuple:
        """ Create the stream of future dates. """
        last_date, _ = self._df.last
        freq = self.frequency

        t = np.arange(1., round(self._fp * freq) + .001)
        ft = [
            last_date + np.timedelta64(round(12 * v / freq), 'M').astype('timedelta64[D]')
            for v in t
        ]

        return t, ft

    def _calculate(self) -> None:
        self._last_price = self.get_last_price()
        self._t, ft = self._get_future_dates()
        div_drift_annual = self._calc_drift()

        country = self._eq.country
        gdp_rate = self._rf \
            .get_gdp(country) \
            .prices.values
        gdp = np.nanmean(gdp_rate[-6:])
        inflation_rate = self._rf \
            .get_inflation(country) \
            .prices.values
        inflation = np.nanmean(inflation_rate[-13:])

        div_drift_annual = min(
            div_drift_annual,
            gdp + inflation
        )
        self._div_drift = Math.compound(
            div_drift_annual,
            1. / self.frequency
        )

        # Create cash flows sequence and calculate final price
        cf = self._df.last[1] + np.zeros(len(self._t))
        self._cf_no_growth = np.array([self._t, cf])
        self._pn_no_growth = float(self._cf_no_growth[1, -1])

        # Calculate the DCF w/ growth
        cf_compound = cf * (Math.compound(self._div_drift, self._t) + 1.)
        self._cf_growth = np.array([self._t, cf_compound])
        self._pn_growth = float(self._cf_growth[1, -1]) * (1. + self._div_drift)

        # Transform projected dividend series for plotting
        self._cf_zg = np.array([ft, cf])
        self._cf_gwt = np.array([ft, cf_compound])

        divs = self._df.dividends
        self._div_ts = pd.Series(divs[1], index=divs[0])

    def _otf_calculate(self, **kwargs) -> dict:
        """ In input give the annual required rate of return. If not supplied,
            the equity cost is calculated as:
                dr = yield + drift - yield_gvt
        """

        dr = kwargs.get('d_rate', None)
        if dr is None:
            dr = self._df.ttm_yield()
            try:
                rf = Fin.get_rf_glob() \
                    .get_rf(self._asset.country) \
                    .last_price()[0]
            except Ex.MissingData:
                rf = .0
            dr -= rf

        den = Math.compound(dr, 1. / self.frequency)
        dr = den + self._div_drift

        # Check model consistency
        if den <= 0.:
            msg = f'Re={dr:.1%} < g={self._div_drift:.1%} for {self._uid}'
            raise ValueError(msg)

        n = self._cf_no_growth.shape[1]
        terminal_dcf = (1. + dr) ** n
        fv_zg = float(np.sum(Math.dcf(self._cf_no_growth, dr)))
        pn_zg = self._pn_no_growth / terminal_dcf / den
        fv_zg += pn_zg
        fv_gwt = float(np.sum(Math.dcf(self._cf_growth, dr)))
        pn_gwt = self._pn_growth / terminal_dcf / den
        fv_gwt += pn_gwt

        ret_zg = fv_zg / self._last_price - 1.
        ret_gwt = fv_gwt / self._last_price - 1.

        return {
            'uid': self._uid,
            'ccy': self._asset.currency,
            'equity': self._eq.uid,
            'future_dates': self._t,
            'div_num': self._df.num,
            'div_freq': self.frequency,
            'div_ts': self._div_ts,
            'last_price': self._last_price,
            'div_drift': self._div_drift,
            'div_zg': self._cf_zg,
            'div_gwt': self._cf_gwt,
            'd_rate': dr,
            'fair_value_no_growth': fv_zg,
            'fair_value_with_growth': fv_gwt,
            'ret_no_growth': ret_zg,
            'ret_with_growth': ret_gwt
        }


def DDModel(company: str, projection: int,
            d_rate: Optional[float] = None) -> DDMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return DividendDiscountModel(company, projection) \
        .result(d_rate=d_rate)
