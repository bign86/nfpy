#
# Building Blocks
# Functions and objects for equity valuation
#

import cutils
from dataclasses import dataclass
import numpy as np
import pandas.tseries.offsets as off

from nfpy import Math
from nfpy.Assets import (get_af_glob, TyAsset)
import nfpy.Calendar as Cal
from nfpy.Session import get_session
from nfpy.Tools import (Constants as Cn, get_logger_glob, Exceptions as Ex)

from .Beta import Beta


@dataclass(eq=False, order=False, frozen=True)
class CAPMResult(object):
    uid: str
    market: str

    start: np.datetime64
    end: np.datetime64
    frequency: Cal.Frequency
    horizon: Cal.Horizon

    cost_of_equity: float | np.ndarray
    risk_premium: float | np.ndarray
    unlevered: bool
    beta: float | np.ndarray
    rf: float | np.ndarray


class CAPM(object):
    """ Calculates the CAPM model. """

    def __init__(
        self,
        eq: str | TyAsset,
        freq: Cal.Frequency,
        index: str | TyAsset | None = None,
        start: Cal.TyDate | None = None,
        end: Cal.TyDate | None = None,
        horizon: Cal.Horizon | None = None
    ):
        # Set the session
        self._s = get_session()

        # Set the time limits in the series. Start the series one data point
        # later to account for the data point lost in calculating the returns.
        # As everything is resampled on the same frequency, the slice should
        # be the same for all series.
        dt_off = {
            Cal.Frequency.B: (lambda v: v, lambda v: v),
            Cal.Frequency.D: (lambda v: v, lambda v: v),
            Cal.Frequency.M: (Cal.to_month_begin, Cal.to_previous_month_end),
            Cal.Frequency.Y: (Cal.to_year_begin, Cal.to_previous_year_end),
        }
        try:
            offset = dt_off[freq]
        except KeyError:
            raise Ex.CalendarError(f'CAPM(): frequency {freq.value} not supported')

        # Handle dates
        if end is not None:
            end = Cal.any2np(end)
        elif self._s:
            end = self._s.calendar.t0.asm8
        else:
            raise Ex.CalendarError(f'CAPM(): with no session, end date must be provided')

        if start is not None:
            start = Cal.any2np(start)
        elif horizon is not None:
            start = end - off.DateOffset(months=horizon.months)
        elif self._s:
            start = self._s.calendar.start.asm8
        else:
            raise Ex.CalendarError(f'CAPM(): with no session, a start date or horizon must be provided')

        self._start = offset[0](start)
        self._end = offset[1](end)

        if self._s:
            # Check if the calendar supports us
            if start < self._s.calendar.start:
                raise Ex.CalendarError(
                    f'Beta(): start date {start} < calendar start {self._s.calendar.start}'
                )

        self._af = get_af_glob()

        if isinstance(eq, str):
            eq = self._af.get(eq)

        if not eq.type == 'Equity':
            raise Ex.AssetTypeError(f'CAPM(): {eq.uid} is not an equity but a {eq.type}')

        self._eq = eq

        if index is None:
            self._idx = self._af.get(self._eq.index)
        else:
            if isinstance(index, str):
                self._idx = self._af.get(index)
            else:
                self._idx = index

        self._freq = freq
        self._horizon = horizon

        # Log
        get_logger_glob().info(
            f'CAPM: {self._eq.uid} freq={freq.value} '
            f'start={self._start} end={self._end}'
        )

        # Get the market prices given the desired frequency
        idx_p = self._idx \
            .prices(start, end) \
            .resample(self._freq.to_end) \
            .agg('last')
        idx_r = cutils.ret_nans(idx_p.to_numpy(), False)

        # Cut to length
        self._idx_r = Math.trim_ts(
            idx_p.index.to_numpy(),
            idx_r,
            start=self._start,
            end=self._end
        )[1]

        # Get the risk-free and cut to length
        rfree_r = self._af \
            .get_rf(self._eq.currency) \
            .prices(start, end) \
            .resample(self._freq.to_end) \
            .agg('last')

        dt_rf, rfree_r, slc = Math.trim_ts(
            rfree_r.index.to_numpy(),
            rfree_r.to_numpy(),
            start=self._start,
            end=self._end
        )

        # Get the risk-free as the last value averaging over the same
        # amount of data as the frequency
        self._rfree = Math.last_valid_value(rfree_r)[0]

        # Calculate the risk premium using both arithmetic and geometric average
        # and taking the average of the two
        annualization = {
            Cal.Frequency.B: Cn.BDAYS_IN_1Y,
            Cal.Frequency.D: Cn.BDAYS_IN_1Y,
            Cal.Frequency.M: Cn.MONTHS_IN_1Y,
            Cal.Frequency.Y: 1,
        }
        rm_geo = Math.compound(
            np.nancumprod(1. + np.r_[.0, idx_r])[-1] - 1.,
            annualization[freq] / idx_r.shape[0]
        )

        # NOTE: that this assumes that indices are expressed in annualized
        #       units (which is usually the case)
        rf_geo = Math.compound(
            np.nancumprod(1. + np.r_[.0, rfree_r])[-1] - 1.,
            1. / rfree_r.shape[0]
        )
        self._rp = rm_geo - rf_geo

    def results(self, unlever: bool = False) -> CAPMResult:
        dtype = 'Beta.Adjusted.Unlevered' if unlever else 'Beta.Adjusted'

        try:
            beta_obj = self._af.get_derived_series(
                asset1=self._eq.uid,
                asset2=self._idx.uid,
                frequency=self._freq,
                horizon=str(self._horizon)
            )
        except Ex.MissingData as ex:
            beta_res = Beta(
                asset=self._eq,
                freq=self._freq,
                mkt=self._idx,
                start=self._start,
                end=self._end
            ).beta(unlever=unlever)
            beta = beta_res.beta

        else:
            betas = beta_obj.series(dtype)

            if betas.empty:
                beta_res = Beta(
                    asset=self._eq,
                    freq=self._freq,
                    mkt=self._idx,
                    start=self._start,
                    end=self._end
                ).beta(unlever=unlever)
                beta = beta_res.beta

            else:
                beta = Math.last_valid_value(
                    betas.to_numpy(),
                    betas.index.to_numpy(),
                    np.datetime64(self._end, self._freq.value)
                )[0]

        # Final calc
        capm = self._rfree + beta * self._rp

        return CAPMResult(
            uid=self._eq.uid,
            market=self._idx.uid,
            start=self._start,
            end=self._end,
            frequency=self._freq,
            horizon=self._horizon,
            cost_of_equity=capm,
            risk_premium=self._rp,
            unlevered=unlever,
            beta=beta,
            rf=self._rfree
        )
