#
# Dividend Discount Model
# Class to calculate a stock fair value using the DDM
#

import pandas as pd
from typing import Union

import nfpy.Financial as Fin
import nfpy.Financial.Math as Math
from nfpy.Tools import Exceptions as Ex

from .BaseFundamentalModel import BaseFundamentalModel
from .BaseModel import BaseModelResult


class GGMResult(BaseModelResult):
    """ Object containing the results of the Gordon Growth Model. """


class GordonGrowthModel(BaseFundamentalModel):
    """ Gordon Growth Model """

    _RES_OBJ = GGMResult

    def __init__(self, uid: str, date: Union[str, pd.Timestamp] = None,
                 **kwargs):
        super().__init__(uid, date)

        self._df = Fin.DividendFactory(self._eq, self._start, self._t0)
        self._check_applicability()
        self._record_inputs()

    def _record_inputs(self):
        self._res_update(ccy=self._asset.currency, uid=self._uid,
                         equity=self._eq.uid, t0=self._t0, start=self._start)

    def _check_applicability(self):
        """ Check applicability of the DDM model to the equity. The presence
            and frequency of dividends is checked.
        """
        # We assume DDM cannot be used if dividends are NOT paid
        if self._df.num == 0:
            raise Ex.MissingData('No dividends for {}'.format(self._eq.uid))

    def _calc_freq(self):
        """ Calculates model frequency. """
        self._freq = self._df.frequency

    def _calc_drift(self) -> float:
        """ Calculate annualized equity and dividend drifts. """
        # Get dividends drift
        try:
            div_drift = self._df.annualized_drift
        except ValueError:
            div_drift = .0

        return div_drift

    def _calculate(self):
        div_drift = self._calc_drift()
        _, div = self._df.last
        freq = self.frequency

        # Create cash flows sequence and calculate final price
        fut_div = div * (div_drift + 1.) / freq
        self._fut_div = fut_div

        # Record results
        self._res_update(div=div, fut_div=fut_div, div_drift=div_drift,
                         last_price=self.get_last_price())

    def _otf_calculate(self, **kwargs) -> dict:
        """ In input give the annual required rate of return. """

        # If no input is given, take the risk-free rate
        _ = kwargs
        try:
            d_rate = kwargs['d_rate']
        except KeyError:
            rf = Fin.get_rf_glob().get_rf(self._asset.currency)
            d_rate = rf.last_price(self._t0)[0]

        # Check model consistency
        den = d_rate - self._calc_drift()
        if den <= 0.:
            raise ValueError('The discounting of {:.0f}% is negative for {}'
                             .format(den*100., self._uid))

        fv = float(self._fut_div * Math.cdf(den, 1))

        return {'d_rate': d_rate, 'fair_value': fv}


def GGModel(uid: str, date: Union[str, pd.Timestamp] = None) -> GGMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return GordonGrowthModel(uid, date).result()
