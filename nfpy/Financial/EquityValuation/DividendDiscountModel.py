#
# Dividend Discount Model
# Class to calculate a stock fair value using the DDM
#

import numpy as np
import pandas as pd
from typing import Optional

from nfpy.Calendar import TyDate
import nfpy.Financial as Fin
import nfpy.Math as Math
from nfpy.Tools import (Constants as Cn, Exceptions as Ex)

from .BaseFundamentalModel import (BaseFundamentalModel, FundamentalModelResult)


class DDMResult(FundamentalModelResult):
    """ Object containing the results of the Dividend Discount Model. """


class DividendDiscountModel(BaseFundamentalModel):
    """ Dividend Discount Model class. """

    _RES_OBJ = DDMResult

    def __init__(self, uid: str, date: Optional[TyDate] = None,
                 past_horizon: int = 5, future_proj: int = 3,
                 div_conf: float = .1, susp_conf: float = 1., **kwargs):
        super().__init__(uid, date, past_horizon, future_proj)
        self._df = Fin.DividendFactory(self._eq, div_conf, susp_conf)
        self._check_applicability()

        self._res_update(div_conf=div_conf, ccy=self._asset.currency,
                         suspension=susp_conf, uid=self._uid,
                         equity=self._eq.uid, t0=self._t0, start=self._start,
                         past_horizon=self._ph, future_proj=self._fp)

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

    def _calc_freq(self) -> None:
        """ Calculates model frequency. """
        self._freq = self._df.frequency

    def _calc_drift(self) -> tuple:
        """ Calculate annualized equity and dividend drifts. """
        # Get equity drift
        eq_drift = Math.compound(
            self._eq.expct_return(
                start=self._start,
                end=self._t0
            ),
            Cn.BDAYS_IN_1Y
        )

        # Get dividends drift
        try:
            div_drift = self._df.annualized_drift
        except ValueError:
            div_drift = .0

        return eq_drift, div_drift

    def _get_future_dates(self) -> tuple:
        """ Create the stream of future dates. """
        last_date = self._df.dividends[0][-1]
        freq = self.frequency

        t = np.arange(1., round(self._fp * freq) + .001)
        ft = [
            # last_date + pd.DateOffset(months=round(12 * v / freq))
            last_date + np.timedelta64(round(12 * v / freq), 'M').astype('timedelta64[D]')
            for v in t
        ]

        return t, ft

    def _calculate(self) -> None:
        last_price = self.get_last_price()
        eq_drift, div_drift = self._calc_drift()
        dt_ts, div_ts = self._df.dividends
        t, ft = self._get_future_dates()
        fp, freq = self._fp, self.frequency

        # Create cash flows sequence and calculate final price
        cf = div_ts[-1] + np.zeros(len(t))
        final_price = last_price * (Math.compound(eq_drift, fp) + 1.)
        self._cf_no_growth = np.array([t, cf])
        self._cf_no_growth[1, -1] += final_price

        # Calculate the DCF w/ growth
        cf_compound = cf * (Math.compound(div_drift, t, freq) + 1.)
        self._cf_growth = np.array([t, cf_compound])
        self._cf_growth[1, -1] += final_price

        # Transform projected dividend series for plotting
        cf_zg = np.array([ft, cf])
        cf_gwt = np.array([ft, cf_compound])

        # Record results
        self._res_update(div_ts=pd.Series(div_ts, index=dt_ts),
                         div_num=self._df.num,
                         last_price=last_price, div_freq=freq,
                         price_drift=eq_drift, div_drift=div_drift,
                         final_price=final_price, div_zg=cf_zg,
                         div_gwt=cf_gwt, future_dates=t)

    def _otf_calculate(self, **kwargs) -> dict:
        """ In input give the annual required rate of return. """
        # Take the risk free rate
        try:
            rf = Fin.get_rf_glob().get_rf(self._asset.currency)
            dr = rf.last_price(self._t0)[0]
        except Ex.MissingData:
            dr = kwargs.get('d_rate', .0)

        # Obtain the period-rate from the annualized rate
        dr /= self.frequency

        fv_zg = float(np.sum(Math.dcf(self._cf_no_growth, dr)))
        fv_gwt = float(np.sum(Math.dcf(self._cf_growth, dr)))

        last_price = self.get_last_price()
        ret_zg = fv_zg / last_price - 1.
        ret_gwt = fv_gwt / last_price - 1.

        return {'d_rate': dr, 'fair_value_no_growth': fv_zg,
                'fair_value_with_growth': fv_gwt, 'ret_no_growth': ret_zg,
                'ret_with_growth': ret_gwt}


def DDModel(company: str, d_rate: float, date: Optional[TyDate] = None,
            past_horizon: int = 5, future_proj: int = 3,
            div_conf: float = .2) -> DDMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return DividendDiscountModel(
        company,
        date,
        past_horizon,
        future_proj,
        div_conf
    ).result(d_rate=d_rate)
