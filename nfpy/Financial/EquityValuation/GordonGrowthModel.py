#
# Dividend Discount Model
# Class to calculate a stock fair value using the DDM
#

import numpy as np
from typing import Optional

from nfpy.Tools import Exceptions as Ex

from .DDMBase import (DDMBase, DDMResult)


class GordonGrowthModel(DDMBase):
    """ Gordon Growth Model """

    def _calculate(self) -> None:
        self._last_price = self.get_last_price()
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

        self._div_drift = min(
            div_drift_annual,
            gdp + inflation
        )
        self._div = self._df.last[1] * self.frequency
        self._fut_div = self._div * (self._div_drift + 1.)

    def _otf_calculate(self, **kwargs) -> dict:
        """ In input give the annual required rate of return. If not supplied,
            the equity cost is calculated as:
                dr = yield + drift - yield_gvt
        """

        dr = kwargs.get('d_rate', None)
        if dr is None:
            dr = self._df.ttm_yield() + self._div_drift
            try:
                rf = self._rf \
                    .get_rf(self._asset.country) \
                    .last_price()[0]
            except Ex.MissingData:
                rf = .0
            dr -= rf
        # print(f'ttm_yield + div_drift - rf = dr')
        # print(f'{self._df.ttm_yield():.1%} + {self._div_drift:.1%} - {rf:.1%} = {dr:.1%}')

        # Check model consistency
        den = dr - self._div_drift
        if den <= 0.:
            msg = f'Re={dr:.1%} < g={self._div_drift:.1%} for {self._uid}'
            raise ValueError(msg)

        fv_no_gwt = float(self._div / den)
        fv_gwt = float(self._fut_div / den)

        ret_no_gwt = fv_no_gwt / self._last_price - 1.
        ret_gwt = fv_gwt / self._last_price - 1.

        return {
            'uid': self._uid,
            'ccy': self._asset.currency,
            'equity': self._eq.uid,
            'last_price': self._last_price,
            'div': self._div, 'fut_div': self._fut_div,
            'div_drift': self._div_drift,
            'd_rate': dr,
            'fair_value_no_growth': fv_no_gwt,
            'fair_value_with_growth': fv_gwt,
            'ret_no_growth': ret_no_gwt,
            'ret_with_growth': ret_gwt
        }


def GGModel(uid: str, d_rate: Optional[float] = None) -> DDMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return GordonGrowthModel(uid).result(d_rate=d_rate)
