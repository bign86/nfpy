import cutils
from dataclasses import dataclass
import numpy as np
import pandas.tseries.offsets as off
from scipy import stats
from typing import Any

from nfpy.Assets import (get_af_glob, get_fx_glob, TyAsset)
import nfpy.Calendar as Cal
from nfpy.Math.TSStats_ import rolling_sum
from nfpy.Math.TSUtils_ import (search_trim_pos, trim_ts)
from nfpy.Session import get_session
from nfpy.Tools import (get_logger_glob, Exceptions as Ex)

from ..FundamentalsFactory import FundamentalsFactory


@dataclass(eq=False, order=False, frozen=True)
class BetaResult(object):
    uid: str
    mkt: str
    comp: str
    leverage: float | None
    start: Cal.TyDate
    end: Cal.TyDate
    horizon: Cal.Horizon | None
    frequency: Cal.Frequency
    beta: float
    adj_beta: float
    jensen: float
    adj_jensen: float

    def __repr__(self) -> str:
        return f'BetaResult<{self.uid}|{self.mkt}>: @{self.end} {self.beta}'


class Beta(object):

    def __init__(
            self,
            asset: str | TyAsset,
            freq: Cal.Frequency,
            mkt: str | TyAsset | None = None,
            start: Cal.TyDate | None = None,
            end: Cal.TyDate | None = None,
            horizon: Cal.Horizon | None = None,
            comp: str | TyAsset | None = None,
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
            raise Ex.CalendarError(f'Beta(): frequency {freq.value} not supported')

        # Handle dates
        if end is not None:
            end = Cal.any2np(end)
        elif self._s:
            end = self._s.calendar.t0.asm8
        else:
            raise Ex.CalendarError(f'Beta(): with no session, end date must be provided')

        if start is not None:
            start = Cal.any2np(start)
        elif horizon is not None:
            start = end - off.DateOffset(months=horizon.months)
        elif self._s:
            start = self._s.calendar.start.asm8
        else:
            raise Ex.CalendarError(f'Beta(): with no session, a start date or horizon must be provided')

        self._start = offset[0](start)
        self._end = offset[1](end)

        if self._s:
            # Check if the calendar supports us
            if start < self._s.calendar.start:
                raise Ex.CalendarError(
                    f'Beta(): start date {start} < calendar start {self._s.calendar.start}'
                )

        # Get asset objects
        af = get_af_glob()

        # Asset
        if isinstance(asset, str):
            asset = af.get(asset)
        self._asset = asset

        # Benchmark
        if mkt is None:
            if not asset.type == 'Equity':
                raise Ex.AssetTypeError(f'Beta(): cannot get the index of {asset.uid} since is not an equity')
            mkt = af.get(asset.index)
        elif isinstance(mkt, str):
            mkt = af.get(mkt)
        self._mkt = mkt

        # Company for un-levering
        if comp is None:
            if (asset.type == 'Equity') & (asset.company is not None):
                comp = af.get(asset.company)
        elif isinstance(comp, str):
            comp = af.get(comp)

        self._fundamentals = None
        self._comp = None
        if comp is not None:
            if not comp.type == 'Company':
                raise Ex.AssetTypeError(f'Beta(): {comp.uid} is not a company but a {comp.type}')
            self._fundamentals = FundamentalsFactory(comp)
            self._comp = comp

        self._freq = freq
        self._horizon = horizon

        # Log
        get_logger_glob().info(
            f'Beta(): {self._asset.uid}|{self._mkt.uid} freq={freq.value} '
            f'start={self._start} end={self._end}'
        )

        # Resample to desired frequency. As everything is resampled on the same
        # frequency, the slice should be the same for all series.
        asset_p = asset.prices(start, end) \
            .resample(freq.to_end) \
            .agg('last')
        asset_r = cutils.ret_nans(asset_p.to_numpy(), False)

        # Convert index to asset currency
        fx_p = get_fx_glob() \
            .get(mkt.currency, asset.currency) \
            .prices(start, end)
        mkt_p = mkt.prices(start, end) * fx_p

        mkt_p = mkt_p.resample(freq.to_end) \
            .agg('last')
        mkt_r = cutils.ret_nans(mkt_p.to_numpy(), False)

        _, self._asset_r, self._slice = trim_ts(
            asset_p.index.to_numpy(),
            asset_r,
            start=self._start,
            end=self._end
        )
        self._mkt_r = mkt_r[self._slice]

    def beta(
            self,
            unlever: bool = False,
            use_tax_shield: bool = True,
    ) -> BetaResult:
        # Calculate beta
        ols = self._beta(self._asset_r, self._mkt_r)
        beta = ols.slope

        leverage = None

        # Take fundamental data for de-leveraging
        if unlever:
            if self._fundamentals is None:
                raise Ex.MissingData(f'Beta(): cannot unlever {self._asset.uid} as fundamentals are missing')

            # We take the current, not the average, equity/debt ratio
            dt, e = self._fundamentals.total_equity('A')
            d = self._fundamentals.total_debt('A')[1]

            # Calculate where to stop the series
            dt_slice = search_trim_pos(dt, end=self._end)
            stop = (dt_slice.stop - 1) or -1

            # Calculate tax shield if needed
            ts = 1.
            if use_tax_shield:
                t = self._fundamentals.tax_rate('A')[1]
                ts = 1 - np.nanmean(t[dt_slice])

            leverage = 1. + ts * d[stop] / e[stop]
            beta /= leverage

        adj_beta = (2. * beta + 1.) / 3.
        jensen = ols.intercept - (1. - beta)
        adj_jensen = ols.intercept - (1. - adj_beta)

        return BetaResult(
            uid=self._asset.uid,
            mkt=self._mkt.uid,
            comp=self._comp.uid if self._comp is not None else None,
            leverage=leverage,
            start=self._start,
            end=self._end,
            horizon=self._horizon,
            frequency=self._freq,
            beta=beta,
            adj_beta=adj_beta,
            jensen=jensen,
            adj_jensen=adj_jensen,
        )

    @staticmethod
    def _beta(
            asset_r: np.ndarray,
            mkt_r: np.ndarray,
    ) -> Any:
        v = np.vstack((asset_r, mkt_r))
        v = cutils.dropna(v, 1)
        return stats.linregress(v[1, :], v[0, :])


def beta_var(
        dt: np.ndarray,
        ts: np.ndarray,
        mkt: np.ndarray,
        start: np.datetime64 | None = None,
        end: np.datetime64 | None = None
) -> float:
    """ Gives the beta of a series with respect to another (an index).

        Input:
            dt [np.ndarray]: dates series under analysis
            ts [np.ndarray]: return series under analysis
            mkt [np.ndarray]: market proxy return time series
            start [np.datetime64 | None]: start date of the series (Default: None)
            end [np.datetime64 | None]: end date of the series excluded (Default: None)

        Output:
            beta [float]: the beta
    """
    if dt.shape != ts.shape != mkt.shape:
        raise Ex.ShapeError('beta_var(): the series must have the same length')

    slc = search_trim_pos(dt, start=start, end=end)
    v = cutils.dropna(
        np.vstack((ts[slc], mkt[slc])), 1
    )

    prx_var = np.var(v[1, :])
    covar = np.cov(v[0, :], v[1, :], bias=True)

    return covar[0, 1] / prx_var


def beta_ols(
        dt: np.ndarray,
        ts: np.ndarray,
        proxy: np.ndarray,
        w: int | None = None
) -> tuple:
    """ Calculates the beta of a series with respect to a benchmark as the slope
        of the linear regression between the two.

        Input:
            dt [np.ndarray]: dates time series
            ts [np.ndarray]: equity or other series under analysis
            proxy [np.ndarray]: reference proxy time series
            w [int | None]: window size if rolling (Default: None)

        Output:
            dt [np.ndarray | TyDate]: date (only if rolling else None)
            slope [np.ndarray | float]: the beta
            adj_beta [np.ndarray | float]: the adjusted beta
            intercept [np.ndarray | float]: intercept of the regression
    """
    if (dt.shape != ts.shape != proxy.shape) and len(dt.shape) > 1:
        raise Ex.ShapeError('The series must have the same length')

    v = np.vstack((ts, proxy))

    if not w:
        # scipy.linregress() is not robust against nans, therefore we clean them
        # and keep the dates series consistent.
        v = cutils.dropna(v, 1)

        dts = dt[-1:]
        slope, intercept, _, _, std_err = stats.linregress(v[1, :], v[0, :])

    else:
        sumx = rolling_sum(v[1, :], w)
        sumy = rolling_sum(v[0, :], w)
        sumxy = rolling_sum(v[1, :] * v[0, :], w)
        sumxx = rolling_sum(v[1, :] * v[1, :], w)

        slope = (w * sumxy - sumx * sumy) / (w * sumxx - sumx * sumx)
        intercept = (sumy - slope * sumx) / w
        dts = dt[w - 1:]

    adj_beta = (1. + 2. * slope) / 3.

    return dts, slope, adj_beta, intercept
