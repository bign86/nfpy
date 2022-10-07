#
# Generic Dividend Discount Model
# Class to calculate a stock fair value using a multi-stage DDM
#

import numpy as np
from typing import Optional

import nfpy.Math as Math

from .DDMBase import (DDMBase, DDMResult)


class DDM(DDMBase):
    """ Up to three stages can be separately defined. The perpetual stage does
        not need to be defined. The syntax to specify one of the other two
        optional stages is a tuple defined as (<t>, <g>, <H>) where:
            - <t>: duration of the stage in years [mandatory]
            - <g>: dividend growth [optional]
            - <H>: is H-model stage [optional, default False]
    """

    def __init__(self, uid: str, stage1: Optional[tuple] = None,
                 stage2: Optional[tuple] = None, **kwargs):
        super(DDM, self).__init__(uid, **kwargs)

        self._stage1 = stage1
        self._stage2 = stage2

        self._num_stages = sum(
            1 for v in (stage1, stage2)
            if v is not None
        )
        self._fp = sum(
            int(v[0])
            for v in (stage1, stage2)
            if v is not None
        )

    def _get_future_dates(self) -> tuple:
        """ Create the stream of future dates. """
        last_date, _ = self._df.last
        freq = self.frequency

        t = np.arange(1., round(self._fp * freq) + .001)
        dt = [
            last_date + np.timedelta64(round(12 * v / freq), 'M').astype('timedelta64[D]')
            for v in t
        ]

        return t, dt

    def _calculate(self) -> None:
        self._calc_macro_variables()
        t, self._dt = self._get_future_dates()
        d0 = self._df.last[1]

        # If there are suitable stages, go through them
        if self._num_stages == 0:
            self._cf_no_gwt = d0 * self._freq
            self._cf_gwt = self._cf_no_gwt * (1. + self._lt_growth)

        else:
            # Create the no-growth arrays
            cf = d0 + np.zeros(len(t))
            self._pn_no_growth = d0 * self._freq
            self._cf_no_growth = np.array([t, cf])

            # Calculate the growth arrays
            # Create the array of dividends
            fut_rate = np.ones(t.shape[0])
            inv_freq = 1. / self._freq
            rate_lt_pp = Math.compound(self._lt_growth, inv_freq)

            if self._num_stages == 1:
                rate_1 = self._stage1[1]
                if rate_1 is None:
                    rate_1 = self._st_growth

                rate_1_pp = Math.compound(rate_1, inv_freq)
                if self._stage1[2]:
                    fut_rate += abs(rate_1_pp - rate_lt_pp) * (1 + t) / t

                fut_rate += rate_1_pp

            else:
                rate_1 = self._stage1[1]
                if rate_1 is None:
                    rate_1 = self._st_growth

                rate_2 = self._stage2[1]
                if rate_2 is None:
                    rate_2 = 2 * rate_1 - self._lt_growth

                t_1 = self._stage1[0] * self._freq

                rate_1_pp = Math.compound(rate_1, inv_freq)
                rate_2_pp = Math.compound(rate_2, inv_freq)
                if self._stage1[2]:
                    fut_rate[:t_1] += (rate_2_pp - rate_1_pp) * \
                                      (t[:t_1]-1) / t[t_1-1]

                if self._stage2[2]:
                    rate_v = (rate_lt_pp - rate_2_pp) * \
                             (t[t_1:] - t[t_1]) / (len(t) - t[t_1-1])
                    rate_v[np.isnan(rate_v)] = .0
                    fut_rate[t_1:] += rate_v

                fut_rate[:t_1] += rate_1_pp
                fut_rate[t_1:] += rate_2_pp

            self._st_growth = rate_1
            self._rates = (fut_rate - 1.)[:]

            # Calculate the compounded dividends
            fut_rate[0] *= d0
            cf_growth = np.cumprod(fut_rate)

            # Calculate the perpetual part
            self._pn_growth = float(cf_growth[-1]) \
                              * (1. + self._lt_growth) \
                              * self._freq
            self._cf_growth = np.array([t, cf_growth])

            # Transform projected dividend series for plotting
            self._cf_no_gwt = cf
            self._cf_gwt = cf_growth

    def _calc_fv(self, den: float, dr: float) -> tuple:
        """ In input give the annual required rate of return. """

        if self._num_stages == 0:
            fv_no_gwt = float(self._cf_no_gwt / den)
            fv_gwt = float(self._cf_gwt / den)
        else:
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


def DDMModel(company: str, stage1: Optional[tuple] = None,
             stage2: Optional[tuple] = None,
             d_rate: Optional[float] = None) -> DDMResult:
    """ Shortcut for the calculation. Intermediate results are lost. """
    return DDM(company, stage1, stage2).result(d_rate=d_rate)
