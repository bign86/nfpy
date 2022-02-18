#
# Portfolio Engine
# Engine to work with portfolio
#

import numpy as np
import pandas as pd
from typing import (Any, Optional)

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
from nfpy.Financial import DividendFactory
import nfpy.Math as Math
from nfpy.Tools import Constants as Cn


class PortfolioEngine(object):

    def __init__(self, ptf: Ast.TyAsset):
        self._af = Ast.get_af_glob()
        self._cal = Cal.get_calendar_glob()
        self._fx = Ast.get_fx_glob()

        self._ptf = ptf
        self._bmk = ptf.benchmark

        self._slc = Math.search_trim_pos(
            self._cal.calendar.values,
            start=self._ptf.inception_date.asm8
        )
        self._dt = self._cal.calendar.values[self._slc]

        self._pos_val = None
        self._tot_val = None
        self._wgt = None
        self._ret = None

    @property
    def returns(self) -> tuple[np.ndarray, np.ndarray]:
        if self._ret is None:
            self._calc_returns()
        return self._dt, self._ret

    @property
    def total_value(self) -> tuple[np.ndarray, np.ndarray]:
        if self._tot_val is None:
            self._calc_total_value()
        return self._dt, self._tot_val

    @property
    def weights(self) -> np.ndarray:
        if self._wgt is None:
            self._calc_weights()
        return self._wgt

    def _calc_returns(self) -> None:
        """ Get the portfolio price returns by consolidating constituents
            returns and adjusting for the currency.
        """
        uids = self._ptf.constituents_uids
        ccy = self._ptf.currency

        self._ret = np.sum(
            self._ret_matrix(uids, ccy) * self.weights.T,
            axis=0
        )

    def _calc_total_value(self) -> None:
        """ Get the value of each position in the portfolio base currency. """
        # Copy the array to return position values
        pos = np.array(self._ptf.cnsts_df[self._slc])
        uids = list(self._ptf.constituents_uids)
        ccy = self._ptf.currency
        try:
            uids.remove(ccy)
        except ValueError:
            pass

        for i, u in enumerate(uids):
            if self._fx.is_ccy(u):
                pos[:, i] *= self._fx.get(u, ccy) \
                    .prices.values[self._slc]

            else:
                asset = self._af.get(u)
                pos[:, i] *= asset.prices.values[self._slc]
                asset_ccy = asset.currency
                if asset_ccy != ccy:
                    fx_obj = self._fx.get(asset_ccy, ccy)
                    pos[:, i] *= fx_obj.prices.values[self._slc]

        # Forward-fill values
        self._pos_val = Math.ffill_cols(pos, .0)
        self._tot_val = np.sum(self._pos_val, axis=1)

    def _calc_weights(self) -> None:
        """ Calculates constituent weights from portfolio positions. """
        total_value = self.total_value[1]
        self._wgt = self._pos_val / total_value[:, None]

    def _ret_matrix(self, uids: list, ccy: str) -> np.ndarray:
        """ Helper function to create a matrix of returns as <uid, time>.
            It is assumed <time> spans the whole calendar. The base currency
            must be supplied to ensure the correct FX rates are used.

            input:
                uids [list]: list of uids to construct the matrix
                ccy [str]: base currency to translate the returns in

            Output:
                ret [np.ndarray]: matrix of returns
        """
        m = len(uids)
        n = len(self._dt)
        ret = np.empty((m, n), dtype=float)

        for i, u in enumerate(uids):
            if self._fx.is_ccy(u):
                r = .0
                if u != ccy:
                    r = self._fx.get(u, ccy).returns \
                        .values[self._slc]

            else:
                asset = self._af.get(u)
                r = asset.returns.values[self._slc]
                pos_ccy = asset.currency
                if pos_ccy != ccy:
                    rate = self._fx.get(pos_ccy, ccy) \
                        .returns.values[self._slc]
                    r += (1. + r) * rate

            ret[i, :] = r

        return ret

    def correlation(self) -> np.ndarray:
        """ Get the corr_t0elation matrix for the underlying constituents. """
        uids = list(self._ptf.constituents_uids)
        ccy = self._ptf.currency
        try:
            uids.remove(ccy)
        except ValueError:
            pass

        return np.corrcoef(
            Math.dropna(
                self._ret_matrix(uids, ccy),
                axis=0
            )[0]
        )

    def covariance(self) -> np.ndarray:
        """ Get the covariance matrix for the underlying constituents. """
        uids = list(self._ptf.constituents_uids)
        ccy = self._ptf.currency
        try:
            uids.remove(ccy)
        except ValueError:
            pass

        return np.cov(
            Math.dropna(
                self._ret_matrix(uids, ccy),
                axis=0
            )[0]
        )

    def dividends_paid(self) -> np.ndarray:
        """ Returns the series of annual dividends paid. """
        # Create the list of years
        years = np.unique(
            self._cal
                .calendar
                .values
                .astype('datetime64[Y]')
        )
        dividends = np.zeros(years.shape[0])

        for uid in self._ptf.constituents_uids:
            if self._fx.is_ccy(uid):
                continue

            asset = self._af.get(uid)

            if asset.type == 'Equity':
                dt, div = DividendFactory(asset).dividends
                y_dt = dt.astype('datetime64[Y]')

                for n, y in enumerate(years):
                    dividends[n] += np.sum(div[y_dt == y])

        return dividends

    def dividends_ttm(self) -> float:
        """ Returns the dividends paid in the last 365 days. """
        start = self._cal.t0.asm8.astype('datetime64[Y]') - \
                np.timedelta64(Cn.DAYS_IN_1Y, 'D')
        dividends = .0

        for uid in self._ptf.constituents_uids:
            if self._fx.is_ccy(uid):
                continue

            asset = self._af.get(uid)

            if asset.type == 'Equity':
                dt, div = DividendFactory(asset).dividends
                slc = Math.search_trim_pos(dt, start=start)
                dividends += np.sum(div[slc])

        return dividends

    def te(self, bmk: Optional[Ast.TyAsset] = None,
           start: Optional[Cal.TyDate] = None,
           end: Optional[Cal.TyDate] = None, w: Optional[int] = None) \
            -> tuple[np.ndarray, np.ndarray]:

        if bmk is None:
            if self._bmk is None:
                raise ValueError('')
            bmk = self._af.get(self._bmk)

        return Math.te(
            *self.returns,
            bmk.returns.values[self._slc],
            start=start,
            end=end,
            w=w
        )

    def summary(self) -> dict[str, Any]:
        """ Show the portfolio summary in the portfolio base currency. """
        # Run through positions and collect data for the summary
        idx = np.searchsorted(self._dt, self._ptf.date.asm8)
        pos_value = self._pos_val[idx]

        data = [
            (
                p.type, p.uid,
                p.date.strftime('%Y-%m-%d'),
                p.currency,
                p.alp, p.quantity,
                p.alp * p.quantity,
                float(pos_value[k])
            )
            for k, p in enumerate(self._ptf.constituents.values())
        ]

        # Sort accordingly to the key <type, uid>
        data.sort(key=lambda _t: (_t[0], _t[1]))
        cnsts = pd.DataFrame(
            data,
            columns=('type', 'uid', 'date', 'currency', 'alp', 'quantity',
                     'cost (FX)', f'value ({self._ptf.currency})')
        )

        return {
            'uid': self._ptf.uid, 'currency': self._ptf.currency,
            'inception': self._ptf.inception_date,
            'tot_value': pos_value.sum(), 'constituents_data': cnsts,
        }

    # def sector_aggregation(self):
    #     for uid in self._ptf.constituents_uids:
    #         if self._fx.is_ccy(uid):
    #             continue
    #
    #         asset = self._af.get(uid)
    #
    #         if asset.type == 'Equity':
    #             dt, div = DividendFactory(asset).dividends
    #             y_dt = dt.astype('datetime64[Y]')
    #
    #             for n, y in enumerate(years):
    #                 dividends[n] += np.sum(div[y_dt == y])
