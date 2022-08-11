#
# Dividend Discount Model
# Class to calculate a stock fair value using the DDM
#

import numpy as np
import pandas as pd
from typing import Optional

import nfpy.Math as Math

from .DDMBase import (DDMBase, DDMResult)


class DDM2s(DDMBase):
    """ Dividend Discount Model class. """

    def __init__(self, uid: str, projection: int, **kwargs):
        super().__init__(uid, **kwargs)

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
        self._calc_macro_variables()
        self._t, ft = self._get_future_dates()

        st_drift_pp = Math.compound(
            self._st_div_drift,
            1. / self._freq
        )

        # Create cash flows sequence and calculate final price
        d0 = self._df.last[1]
        cf = d0 + np.zeros(len(self._t))
        self._pn_no_growth = d0 * self._freq
        self._cf_no_growth = np.array([self._t, cf])

        # Calculate the DCF w/ growth
        cf_growth = cf * (Math.compound(st_drift_pp, self._t) + 1.)
        self._pn_growth = float(cf_growth[-1]) \
                          * (1. + self._lt_div_drift) \
                          * self._freq
        self._cf_growth = np.array([self._t, cf_growth])

        # Transform projected dividend series for plotting
        self._cf_no_gwt = np.array([ft, cf])
        self._cf_gwt = np.array([ft, cf_growth])

        divs = self._df.dividends
        self._div_ts = pd.Series(divs[1], index=divs[0])

    def _calc_fv(self, den: float, dr: float) -> tuple:
        """ In input give the annual required rate of return. """

        dr_per_period = Math.compound(dr, 1. / self._freq)

        cf_no_growth = self._cf_no_growth.copy()
        cf_no_growth[1, -1] += self._pn_no_growth / den
        fv_no_gwt = float(np.sum(Math.dcf(cf_no_growth, dr_per_period)))

        cf_growth = self._cf_growth.copy()
        cf_growth[1, -1] += self._pn_growth / den
        fv_gwt = float(np.sum(Math.dcf(cf_growth, dr_per_period)))

        ret_no_gwt = fv_no_gwt / self._last_price - 1.
        ret_gwt = fv_gwt / self._last_price - 1.

        return fv_no_gwt, fv_gwt, ret_no_gwt, ret_gwt


def DDM2sModel(company: str, projection: int,
               d_rate: Optional[float] = None) -> DDMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return DDM2s(company, projection).result(d_rate=d_rate)
