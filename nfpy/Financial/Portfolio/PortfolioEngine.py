#
# Portfolio Engine
# Engine to work with portfolio
#

import numpy as np
import pandas as pd
from typing import (Any, Optional)

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
import nfpy.Math as Math
from nfpy.Tools import Constants as Cn


class PortfolioEngine(object):

    def __init__(self, ptf: Ast.TyAsset):
        self._af = Ast.get_af_glob()
        self._cal = Cal.get_calendar_glob()
        self._fx = Ast.get_fx_glob()

        self._ptf = ptf

        self._slc = Math.search_trim_pos(
            self._cal.calendar.values,
            start=self._ptf.inception_date.asm8
        )
        self._dt = self._cal.calendar.values[self._slc]

        self._cum_divs = None
        self._dt_cum_divs = None
        self._pos_val = None
        self._ret = None
        self._tot_val = None
        self._wgt = None

    @property
    def portfolio(self) -> Ast.Asset:
        return self._ptf

    @property
    def positions_value(self) -> tuple[np.ndarray, np.ndarray]:
        if self._pos_val is None:
            self._calc_total_value()
        return self._dt, self._pos_val

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
    def volatility(self) -> np.ndarray:
        return np.nanstd(self.returns[1])

    @property
    def weights(self) -> np.ndarray:
        if self._wgt is None:
            self._calc_weights()
        return self._wgt

    def _calc_cumulated_dividends(self) -> None:
        df_divs = self._ptf.dividends_received
        cum_divs = np.zeros(len(df_divs.index), dtype=float)

        base_ccy = self._ptf.currency
        for ccy in df_divs.columns:
            d = df_divs[ccy] * self._fx.get(ccy, base_ccy).prices
            cum_divs += d.values

        self._cum_divs = cum_divs[self._slc]
        self._dt_cum_divs = df_divs.index.values[self._slc]

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
        """ Get the value of each position in the portfolio base currency.
            The value of the cash accounts *includes* the value of dividends
            paid in that currency.
        """
        # Copy the array to return position values
        pos = np.array(self._ptf.cnsts_df[self._slc])
        uids = list(self._ptf.constituents_uids)
        ccy = self._ptf.currency

        for i, u in enumerate(uids):
            if u == ccy:
                continue

            elif self._fx.is_ccy(u):
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

    def dividends_received_history(self) -> tuple[np.ndarray, np.ndarray]:
        """ Returns the series of the total dividends received in the base
            currency of the portfolio.
        """
        df_divs = self._ptf.dividends_received
        cum_divs = np.zeros(len(df_divs.index), dtype=float)

        base_ccy = self._ptf.currency
        for ccy in df_divs.columns:
            fx = 1.
            if ccy != base_ccy:
                fx = Math.ffill_cols(
                    self._fx.get(ccy, base_ccy)
                    .prices
                    .values
                )
            cum_divs += np.nancumsum(df_divs[ccy].values) * fx

        cum_divs = cum_divs[self._slc]
        dt_cum_divs = df_divs.index.values[self._slc]

        return dt_cum_divs, cum_divs

    def dividends_received_yearly(self) -> tuple[np.ndarray, np.ndarray]:
        """ Returns the series of the total dividends received annually in the
            base currency of the portfolio.
        """
        if self._cum_divs is None:
            self._calc_cumulated_dividends()

        y_dt = self._dt_cum_divs.astype('datetime64[Y]')
        years = np.unique(y_dt)
        dividends = np.zeros(years.shape[0])

        for n, y in enumerate(years):
            dividends[n] += np.nansum(self._cum_divs[y_dt == y])

        return years, dividends

    def dividends_received_ttm(self) -> float:
        """ Returns the dividends received in the last 365 days. """
        if self._cum_divs is None:
            self._calc_cumulated_dividends()

        start = self._cal.t0.asm8.astype('datetime64[Y]') - \
                np.timedelta64(Cn.DAYS_IN_1Y, 'D')
        slc = Math.search_trim_pos(self._dt_cum_divs, start=start)

        return np.nansum(self._cum_divs[slc])

    def performance(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """ Returns the financial performance of the portfolio without the
            effect of deposits and withdrawals.
        """
        dt, value = self.total_value
        cash_ops = self._ptf.cash_ops

        idx = np.searchsorted(dt, cash_ops.index.values)
        cash_v = np.zeros(value.shape[0], dtype=float)
        np.put(cash_v, idx, cash_ops.values)

        # This is necessary to copy over the data of the total_value without
        # overwriting it
        cash_v = value - np.cumsum(cash_v)
        _, divs = self.dividends_received_history()

        return dt, cash_v, cash_v - divs

    def te(self, bmk: Optional[Ast.TyAsset] = None,
           start: Optional[Cal.TyDate] = None,
           end: Optional[Cal.TyDate] = None, w: Optional[int] = None) \
            -> tuple[np.ndarray, np.ndarray]:
        """ Calculates the Tracking Error of the portfolio relative to a
            benchmark.

            Input:
                bmk [np.ndarray]: benchmark return series
                start [np.datetime64]: start date of the series (default: None)
                end [np.datetime64]: end date of the series excluded (default: None)
                w [int]: rolling window size (default: None)

            Output:
                dt [np.ndarray]: TEV dates series
                tev [np.ndarray]: series of TEV
        """
        if bmk is None:
            if self._ptf.benchmark is None:
                raise ValueError('')
            bmk = self._af.get(self._ptf.benchmark)

        return Math.te(
            *self.returns,
            bmk.returns.values[self._slc],
            start=start,
            end=end,
            w=w
        )

    def summary(self) -> dict[str, Any]:
        """ Show the portfolio summary in the portfolio base currency. """
        # We search for the day before t0 since the value of the position at t0
        # will only be fully known the next period
        idx = np.searchsorted(
            self._dt,
            self._cal.shift(self._cal.t0, -1).asm8
        )
        pos_value = self.positions_value[1][idx, None]
        pos_value = pos_value.reshape((self._ptf.num_constituents,))

        data = []
        # NOTE: here we use the positions at t0, while prices are at t0-1
        t0_quantities = self._ptf.cnsts_df.loc[self._cal.t0].values
        for k, p in enumerate(self._ptf.constituents.values()):
            # We check if the position was empty at the time of calculation aka
            # t0. This is the reason we use the history of the position instead
            # of relying on the positions dictionary that only stores the
            # snapshot at calendar end. Calendar end and t0 may not coincide.
            if t0_quantities[k] == .0:
                continue

            ticker = '-'
            if p.type == 'Equity':
                ticker = self._af.get(p.uid).ticker

            data.append((
                p.type, ticker, p.uid,
                p.currency,
                p.alp, p.quantity,
                p.alp * p.quantity,
                float(pos_value[k])
            ))

        ptf_total = pos_value.sum()
        data.append(('Total', '-', '-', '-', None, None, None, ptf_total))

        # Sort accordingly to the key <type, uid>
        data.sort(key=lambda _t: (_t[0], _t[1], _t[2]))
        cnsts = pd.DataFrame(
            data,
            columns=('type', 'ticker', 'uid', 'currency', 'alp',
                     'quantity', 'cost (FX)', f'value ({self._ptf.currency})')
        )

        # Calculate total deposits/withdrawals
        cash_ops = self._ptf.cash_ops.values
        tot_deposits = np.sum(cash_ops[cash_ops > 0])
        tot_withdrawals = - np.sum(cash_ops[cash_ops < 0])

        return {
            'uid': self._ptf.uid, 'currency': self._ptf.currency,
            'inception': self._ptf.inception_date,
            'tot_value': ptf_total, 'constituents_data': cnsts,
            'tot_deposits': tot_deposits, 'tot_withdrawals': tot_withdrawals
        }

    def country_concentration(self, date: Optional[Cal.TyDate] = None) \
            -> tuple[list[str], np.ndarray]:
        """ Returns the weights of the country exposures at the given date.

            Input:
                date [TyDate]: date at which get exposures

            Output:
                countries [list[str]]: list of countries
                res [np.ndarray]: weights array
        """
        if self._pos_val is None:
            self._calc_total_value()

        data = []
        for uid in self._ptf.constituents_uids:
            p = self._ptf.constituents[uid]
            if p.type in ('Equity', 'Bond'):
                country = self._af.get(uid).country
            elif p.type == 'Cash':
                country = self._fx.get_ccy(uid)[2]
            else:
                raise NotImplementedError(f'{p.type} not implemented, please check!')
            data.append(country)

        countries = sorted(set(data))

        aggregated_v = np.zeros(len(countries))
        dt_idx = -1 if date is None else np.searchsorted(self._dt, date)

        for n, d in enumerate(data):
            idx = countries.index(d)
            aggregated_v[idx] += self._pos_val[dt_idx, n]

        return countries, aggregated_v / self._tot_val[dt_idx]

    def currency_concentration(self, date: Optional[Cal.TyDate] = None) \
            -> tuple[list[str], np.ndarray]:
        """ Returns the weights of the currency exposures at the given date.

            Input:
                date [TyDate]: date at which get exposures

            Output:
                ccys [list[str]]: list of currencies
                res [np.ndarray]: weights array
        """
        if self._pos_val is None:
            self._calc_total_value()

        ccys = [
            k for k, p in self._ptf.constituents.items()
            if p.type == 'Cash'
        ]
        aggregated_v = np.zeros(len(ccys))
        dt_idx = -1 if date is None else np.searchsorted(self._dt, date)

        for n, uid in enumerate(self._ptf.constituents_uids):
            p = self._ptf.constituents[uid]
            idx = ccys.index(p.currency)
            aggregated_v[idx] += self._pos_val[dt_idx, n]

        return ccys, aggregated_v / self._tot_val[dt_idx]

    def sector_concentration(self, date: Optional[Cal.TyDate] = None) \
            -> tuple[list[str], np.ndarray]:
        """ Returns the weights of the sector exposures at the given date.

            Input:
                date [TyDate]: date at which get exposures

            Output:
                ind [list[str]]: list of sectors
                res [np.ndarray]: weights array
        """
        if self._pos_val is None:
            self._calc_total_value()

        data = []
        for uid in self._ptf.constituents_uids:
            p = self._ptf.constituents[uid]
            if p.type == 'Equity':
                company = self._af.get(uid).company
                sector = self._af.get(company).sector
            elif p.type == 'Cash':
                sector = 'Cash'
            else:
                raise NotImplementedError(f'{p.type} not implemented, please check!')
            data.append(sector)

        sectors = sorted(set(data))

        aggregated_v = np.zeros(len(sectors))
        dt_idx = -1 if date is None else np.searchsorted(self._dt, date)

        for n, d in enumerate(data):
            idx = sectors.index(d)
            aggregated_v[idx] += self._pos_val[dt_idx, n]

        return sectors, aggregated_v / self._tot_val[dt_idx]
