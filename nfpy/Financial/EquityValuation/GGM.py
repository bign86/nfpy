#
# Dividend Discount Model
# Class to calculate a stock fair value using the DDM
#

from typing import Optional

from .DDMBase import (DDMBase, DDMResult)


class GGM(DDMBase):
    """ Gordon Growth Model """

    def _calculate(self) -> None:
        self._calc_macro_variables()
        self._cf_no_gwt = self._df.last[1] * self.frequency
        self._cf_gwt = self._cf_no_gwt * (1. + self._lt_growth)
        self._rates = self._lt_growth

    def _calc_fv(self, den: float, dr: float) -> tuple:
        """ In input give the annual required rate of return. """
        _ = dr

        fv_no_gwt = float(self._cf_no_gwt / den)
        fv_gwt = float(self._cf_gwt / den)

        ret_no_gwt = fv_no_gwt / self._last_price - 1.
        ret_gwt = fv_gwt / self._last_price - 1.

        return fv_no_gwt, fv_gwt, ret_no_gwt, ret_gwt


def GGMModel(uid: str, d_rate: Optional[float] = None) -> DDMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return GGM(uid).result(d_rate=d_rate)
