
import cutils
from dataclasses import dataclass
import numpy as np

from nfpy.Assets import (get_af_glob, TyAsset)
import nfpy.Calendar as Cal
from nfpy.Math.TSUtils_ import search_trim_pos


@dataclass(eq=False, order=False, frozen=True)
class RiskPremiumResult(object):
    mkt: str
    rf: str
    start: Cal.TyDate
    end: Cal.TyDate
    frequency: Cal.Frequency
    rp: float

    def __repr__(self) -> str:
        return f'RiskPremiumResult<{self.mkt}|{self.rf}>: @{self.end.strftime("%Y%m%d")} {self.rp}'


_ANNUALIZATION = {
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
            start: Cal.TyDate = None,
            end: Cal.TyDate = None,
    ):
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
        mkt_p = mkt.prices \
            .resample(freq.value) \
            .agg('last')
        self._mkt_r = cutils.ret_nans(mkt_p.to_numpy(), False)

        self._rf_r = rf.prices \
            .resample(freq.value) \
            .agg('last')
        self._freq = freq

        # Set the time limits in the series. Start the series one data point
        # later to account for the data point lost in calculating the returns.
        # As everything is resampled on the same frequency, the slice should
        # be the same for all series.
        calendar = Cal.get_calendar_glob()
        self._start = start or calendar.start
        self._end = end or calendar.end

        dt = mkt_p.index.to_numpy()
        self._slice = search_trim_pos(dt, start=self._start, end=self._end)

    def rp(self) -> RiskPremiumResult:
        periods = _ANNUALIZATION[self._freq]
        mkt_r = self._mkt_r[self._slice]
        rf_r = self._rf_r[self._slice]

        # This calculation calculates a risk premium per period and then
        # aggregates using the geometric average
        rp = mkt_r - (rf_r / periods)
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
            frequency=self._freq,
            rp=rp,
        )
