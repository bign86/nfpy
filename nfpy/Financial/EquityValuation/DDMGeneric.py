#
# Generic Dividend Discount Model
# Class to calculate a stock fair value using a multi-stage DDM
#

import numpy as np
from typing import Optional

from nfpy.Calendar import TyDate
import nfpy.Math as Math

from .DDMBase import DDMBase


class DDMGeneric(DDMBase):

    def __init__(self, uid: str, stages: tuple, **kwargs):
        super(DDMGeneric, self).__init__(uid)

        self._stages = stages

    def _get_future_dates(self) -> tuple:
        """ Create the stream of future dates. """
        last_date, _ = self._df.last
        freq = self.frequency

        tot_l = sum([v[0] * freq for v in self._stages[:-1]])
        t = np.arange(1., round(tot_l) + .001)
        ft = [
            last_date + np.timedelta64(round(12 * v / freq), 'M').astype('timedelta64[D]')
            for v in t
        ]

        return t, ft

    def _calculate(self) -> None:
        self._last_price = self.get_last_price()
        self._t, ft = self._get_future_dates()

        # Calculate the actual drift
        div_drift_annual = self._calc_drift()

        # Calculates max drift
        country = self._eq.country
        gdp_rate = self._rf \
            .get_gdp(country) \
            .prices.values
        gdp = np.nanmean(gdp_rate[-6:])
        inflation_rate = self._rf \
            .get_inflation(country) \
            .prices.values
        inflation = np.nanmean(inflation_rate[-13:])
        macro_drift = gdp + inflation

        # If there are suitable stages, go through them
        num_stages = len(self._stages)
        if num_stages == 1:
            div_drift_annual = Math.compound(
                div_drift_annual,
                1. / self.frequency
            )

        div_drift_annual = min(
            div_drift_annual,
            macro_drift
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
