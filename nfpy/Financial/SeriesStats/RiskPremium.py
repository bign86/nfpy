import cutils
from dataclasses import dataclass
import numpy as np
import pandas.tseries.offsets as off

from nfpy.Assets import (get_af_glob, TyAsset)
import nfpy.Calendar as Cal
from nfpy.Math.TSUtils_ import trim_ts
from nfpy.Session import get_session
from nfpy.Tools import (get_logger_glob, Exceptions as Ex)


@dataclass(eq=False, order=False, frozen=True)
class RiskPremiumResult(object):
    mkt: str
    rf: str
    start: Cal.TyDate
    end: Cal.TyDate
    horizon: Cal.Horizon
    frequency: Cal.Frequency
    rp: float

    def __repr__(self) -> str:
        return f'RiskPremiumResult<{self.mkt}|{self.rf}>: @{Cal.any2pd(self.end).strftime("%Y%m%d")} {self.rp}'


_ANNUALIZATION = {
    Cal.Frequency.B: Cal.BDAYS_IN_1Y,
    Cal.Frequency.D: Cal.BDAYS_IN_1Y,
    Cal.Frequency.M: Cal.MONTHS_IN_1Y,
    Cal.Frequency.Y: 1
}


class RiskPremium(object):
    def __init__(
            self,
            mkt: str | TyAsset,
            rf: str | TyAsset,
            freq: Cal.Frequency,
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
            raise Ex.CalendarError(f'RiskPremium(): frequency {freq.value} not supported')

        # Handle dates
        if end is not None:
            end = Cal.any2np(end)
        elif self._s:
            end = self._s.calendar.t0.asm8
        else:
            raise Ex.CalendarError(f'RiskPremium(): with no session, end date must be provided')

        if start is not None:
            start = Cal.any2np(start)
        elif horizon is not None:
            start = end - off.DateOffset(months=horizon.months)
        elif self._s:
            start = self._s.calendar.start.asm8
        else:
            raise Ex.CalendarError(f'RiskPremium(): with no session, a start date or horizon must be provided')

        self._start = offset[0](start)
        self._end = offset[1](end)

        if self._s:
            # Check if the calendar supports us
            if start < self._s.calendar.start:
                raise Ex.CalendarError(
                    f'RiskPremium(): start date {start} < calendar start {self._s.calendar.start}'
                )

        # Get asset objects
        af = get_af_glob()

        # Market
        if isinstance(mkt, str):
            mkt = af.get(mkt)
        self._mkt = mkt

        # Risk-free
        if isinstance(rf, str):
            rf = af.get(rf)
        self._rf = rf

        # Resample to desired frequency. As everything is resampled on the same
        # frequency, the slice should be the same for all series.
        mkt_p = mkt.prices(start, end) \
            .resample(freq.value) \
            .agg('last')
        mkt_r = cutils.ret_nans(mkt_p.to_numpy(), False)

        rf_r = rf.prices(start, end) \
            .resample(freq.value) \
            .agg('last')
        self._freq = freq
        self._horizon = horizon

        # Log
        get_logger_glob().info(
            f'RiskPremium: {self._mkt.uid}|{self._rf.uid} freq={freq.value} '
            f'start={self._start} end={self._end}'
        )

        _, self._mkt_r, self._slice = trim_ts(
            mkt_p.index.to_numpy(),
            mkt_r,
            start=self._start,
            end=self._end
        )
        self._rf_r = rf_r[self._slice]

    def rp(self) -> RiskPremiumResult:
        periods = _ANNUALIZATION[self._freq]

        # This calculation calculates a risk premium per period and then
        # aggregates using the geometric average
        rp = self._mkt_r - (self._rf_r / periods)
        rp = np.nanprod(1. + rp) ** (periods / rp.shape[0]) - 1.

        # This calculation (not in use) calculates the geometric average first
        # and later calculates the risk premium
        # rm = np.nanprod(1. + mkt_r) ** (periods / mkt_r.shape[0]) - 1.
        # rf = np.nanprod(1. + rf_r) ** (1. / mkt_r.shape[0]) - 1.
        # rp = rm - rf

        return RiskPremiumResult(
            mkt=self._mkt.uid,
            rf=self._rf.uid,
            start=self._start,
            end=self._end,
            horizon=self._horizon,
            frequency=self._freq,
            rp=rp,
        )
