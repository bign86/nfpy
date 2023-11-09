#
# Portfolio Engine
# Work with portfolios
#

from collections import defaultdict
import cutils
import numpy as np
import pandas as pd
import pandas.tseries.offsets as off
from typing import (Any, Iterable)

from .Optimization import optimize_portfolio
from .Utils import _ret_matrix

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
import nfpy.Math as Math


class PortfolioEngine(object):

    def __init__(self, ptf: Ast.TyAsset):
        self._af = Ast.get_af_glob()
        self._cal = Cal.get_calendar_glob()
        self._fx = Ast.get_fx_glob()

        self._ptf = ptf

        self._slc = Math.search_trim_pos(
            self._cal.calendar.values,
            start=self._ptf.inception_date.asm8,
            end=self._cal.t0.asm8
        )
        self._dt = self._cal.calendar.values[self._slc]

        self._curr_pos_val = None
        self._curr_tot_val = None
        self._curr_wgt = None

    @property
    def portfolio(self) -> Ast.Asset:
        return self._ptf

    @property
    def positions_value(self) -> np.ndarray:
        if self._curr_pos_val is None:
            self._calc_curr_values()
        return self._curr_pos_val

    @property
    def value(self) -> float:
        """ Returns the current value of the portfolio in base currency. """
        if self._curr_tot_val is None:
            self._calc_curr_values()
        return self._curr_tot_val

    @property
    def weights(self) -> np.ndarray:
        """ Returns the current weights of the portfolio in base currency. """
        if self._ptf.weights is None:
            self._calc_curr_weights()
        return self._ptf.weights

    def _calc_curr_values(self) -> None:
        """ Get the current value of the portfolio in base currency. """
        base_ccy = self._ptf.currency
        pos_values = np.empty(len(self._ptf.constituents), dtype=float)

        # We put in the base cash account at the end
        pos_values[-1] = self._ptf \
            .constituents[base_ccy] \
            .quantity

        # We add all other positions
        for i, uid in enumerate(self._ptf.constituents_uids):
            pos = self._ptf.constituents[uid]

            if pos.type == 'Cash':
                fx = self._fx \
                    .get(uid, base_ccy) \
                    .prices \
                    .to_numpy()
                fx = Math.last_valid_value(fx[self._slc])
                pos_values[i] = pos.quantity * fx[0]

            else:
                p = self._af \
                    .get(uid) \
                    .prices \
                    .to_numpy()
                p = Math.last_valid_value(p[self._slc])
                fx = (1.,)
                if pos.currency != base_ccy:
                    fx = self._fx \
                        .get(pos.currency, base_ccy) \
                        .prices \
                        .to_numpy()
                    fx = Math.last_valid_value(fx[self._slc])
                pos_values[i] = pos.quantity * fx[0] * p[0]

        self._curr_pos_val = pos_values
        self._curr_tot_val = np.sum(pos_values)

    def _calc_curr_weights(self) -> None:
        """ Calculates constituent weights from portfolio positions. """
        value = self.value
        curr_wgt = self._curr_pos_val / value
        self._ptf.weights = curr_wgt

    def _load_ptf_history(self):
        """ Load the entire history of the portfolio.
            For each given day the order of events is,
                1. Normal time trades
                2. Splits (@ close)
                3. Trades (fractional @ close)
                4. Positions

            FIXME: missing features
                1. Spin-offs are not accounted for
                2. Cash positions do not consider dividends
        """
        pos_hist = self._ptf._load_pos_hist()
        trd_hist = self._ptf._load_trades()

        eq_list = set(p[2] for p in pos_hist if p[3] == 'Equity')
        spl_hist = self._load_splits(eq_list)

        # Create a dictionary of dates with "events"
        events = defaultdict(dict)
        event_dates = set()

        for i, pos in enumerate(pos_hist):
            dt = pos[1].date()
            e = events.get(dt, defaultdict(list))
            e['p'].append(i)
            events[dt] = e
            event_dates.add(dt)

        for i, trd in enumerate(trd_hist):
            dt = trd[1].date()
            e = events.get(dt, defaultdict(list))
            if self._fx.is_ccy(trd[2]):
                e['t'].append(i)
            else:
                _type = 't' if trd[5].is_integer() else 'ft'
                e[_type].append(i)
            events[dt] = e
            event_dates.add(dt)

        for uid, series in spl_hist.items():
            for time, val in series.items():
                dt = (time - off.BDay(1)).date()
                e = events.get(dt, defaultdict(list))
                e['s'].append((uid, time))
                events[dt] = e
                event_dates.add(dt)

        # Get a sorted unique list of dates with events
        event_dates = sorted(event_dates)

        # Branch out depending on whether the inception is inside or outside
        # the span of the calendar.
        if self._ptf.inception_date >= self._cal.start:
            df = pd.DataFrame(index=self._cal.calendar)
            df.loc[self._ptf.inception_date, self._ptf.currency] = .0

            positions = {}

            for date in event_dates:
                tstamp = pd.Timestamp(date)
                date_events = events[date]

                # First apply the trades
                for i in date_events['t']:
                    trade = trd_hist[i]
                    uid = trade[2]
                    side = trade[3]
                    ccy = trade[4]
                    q = trade[5]
                    p = trade[6]
                    costs = trade[7]
                    if side == 1:
                        delta_q = q
                        delta_cash = -q * p - costs
                    else:
                        delta_q = -q
                        delta_cash = q * p - costs
                    position = positions.get(uid, .0)
                    position += delta_q
                    cash = positions.get(ccy, .0)
                    cash += delta_cash

                    positions[uid] = position
                    positions[ccy] = cash
                    df.loc[tstamp, uid] = position
                    df.loc[tstamp, ccy] = cash

                # Apply splits
                # The split if applied the day before as the adjusting trades
                # are executed the daz before.
                for uid, time in date_events['s']:
                    split = spl_hist[uid].at[time]
                    position = positions.get(uid, .0)
                    position /= split
                    positions[uid] = position
                    df.loc[tstamp, uid] = position

                # Apply fractional trades to clean up after splits
                # FIXME: This does not work if fractional trades are allowed.
                #        It must be checked the trading phase. If is 'closing'
                #        the trade should be accounted for in the position the
                #        day after. The fact is fractional is irrelevant.
                for i in date_events['ft']:
                    trade = trd_hist[i]
                    uid = trade[2]
                    side = trade[3]
                    ccy = trade[4]
                    q = trade[5]
                    p = trade[6]
                    costs = trade[7]
                    if side == 1:
                        delta_q = q
                        delta_cash = -q * p - costs
                    else:
                        delta_q = -q
                        delta_cash = q * p - costs
                    position = positions.get(uid, .0)
                    position += delta_q
                    cash = positions.get(ccy, .0)
                    cash += delta_cash

                    positions[uid] = position
                    positions[ccy] = cash
                    df.loc[tstamp, uid] = position
                    df.loc[tstamp, ccy] = cash

                # Check the position
                for i in date_events['p']:
                    pos = pos_hist[i]
                    uid = pos[2]
                    position = positions.get(uid, .0)

                    # Cash positions are never exact due to dividends and fees.
                    # We therefore "reset" the position whenever we know exact
                    # values.
                    # TODO: calculate and log the deviation of the cash position
                    #       <time_between_pos>, <abs. dev.>, <perc. dev.>
                    #       for each cash position.
                    if pos[3] == 'Cash':
                        df.loc[tstamp, uid] = pos[5]
                    else:
                        assert position == pos[5], \
                            f'PortfolioEngine(): {uid}: {position:.5f} != {pos[5]:.5f} @ {date}'

        else:
            # TODO: to do the case in which the inception is before the start
            #       of the calendar.
            pass
        # Go through the list of events and apply them in the appropriate order

        self._ptf._is_history_loaded = True

    def _load_splits(self, eq_uids: Iterable) -> dict[str, pd.Series]:
        """ Fetch the list of splits for all equities in the portfolio. """
        return {
            u: self._af.get(u).splits.dropna()
            for u in eq_uids
        }

    def correlation(self) -> np.ndarray:
        """ Get the correlation matrix for the underlying constituents. """
        ret_matrix = _ret_matrix(
            self._ptf.constituents_uids,
            self._ptf.currency
        )[:, self._slc]
        v = cutils.dropna(ret_matrix, 1)

        return np.corrcoef(v)

    def covariance(self) -> np.ndarray:
        """ Get the covariance matrix for the underlying constituents. """
        ret_matrix = _ret_matrix(
            self._ptf.constituents_uids,
            self._ptf.currency
        )[:, self._slc]
        v = cutils.dropna(ret_matrix, 1)

        return np.cov(v)

    def optimize(self, method: str, parameters: dict[str, Any]):
        """ Prepare the data for optimizers and launch a portfolio optimization.

            Input:
                method [str]: indicated which optimization we want
                parameters [dict[str, Any]]: parameters to use for the
                    optimization
        """
        labels = []
        for i, uid in enumerate(self._ptf.constituents_uids):
            pos = self._ptf.constituents[uid]
            if pos.type == 'Equity':
                tck = self._af.get(uid).ticker
                labels.append(tck)
            else:
                labels.append(uid)

        return optimize_portfolio(
            method, parameters,
            self._ptf.constituents_uids,
            self._ptf.currency,
            self._slc,
            labels
        )

    def pdi(self) -> float:
        """ Calculates the Portfolio Diversification Index """
        return Math.pdi(self.covariance())

    def summary(self) -> dict[str, Any]:
        """ Show the portfolio summary at t0 in the portfolio base currency. """

        # We search for the day before t0 since the value of the position at t0
        # will only be fully known the next period
        pos_value = self.positions_value  # [1][idx, None]

        # The base currency position is always the first
        p = self._ptf.constituents[self._ptf.currency]
        data = [
            (
                p.type, p.uid, '-',
                p.currency,
                p.quantity, p.alp,
                p.alp * p.quantity,
                float(pos_value[0])
            )
        ]
        # here we use the positions at t0, while prices are at t0-1
        # for k, p in enumerate(self._ptf.constituents.values()):
        for i, u in enumerate(self._ptf.constituents_uids, 1):
            p = self._ptf.constituents[u]

            # We check if the position was empty at the time of calculation aka
            # t0. This is the reason we use the history of the position instead
            # of relying on the positions dictionary that only stores the
            # snapshot at calendar end. Calendar end and t0 may not coincide.
            # if t0_quantities[k] == .0:
            #     continue

            ticker = '-'
            if p.type == 'Equity':
                ticker = self._af.get(p.uid).ticker

            data.append((
                p.type, p.uid, ticker,
                p.currency,
                p.quantity, p.alp,
                p.alp * p.quantity,
                float(pos_value[i])
            ))

        ptf_total = pos_value.sum()
        data.append(('Total', '-', '-', '-', None, None, None, ptf_total))

        # Sort accordingly to the key <type, uid>
        data.sort(key=lambda _t: (_t[0], _t[2], _t[1]))
        cnsts = pd.DataFrame(
            data,
            columns=['type', 'uid', 'ticker', 'currency', 'quantity',
                     'alp', 'cost basis', f'value ({self._ptf.currency})']
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

    def country_concentration(self) \
            -> tuple[list[str], np.ndarray]:
        """ Returns the weights of the country exposures at the given date.

            Input:
                date [TyDate]: date at which get exposures

            Output:
                countries [list[str]]: list of countries
                res [np.ndarray]: weights array
        """
        pos_value = self.positions_value

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

        for n, d in enumerate(data):
            idx = countries.index(d)
            aggregated_v[idx] += pos_value[n]

        return countries, aggregated_v / self._curr_tot_val

    def currency_concentration(self) \
            -> tuple[list[str], np.ndarray]:
        """ Returns the weights of the currency exposures at the given date.

            Input:
                date [TyDate]: date at which get exposures

            Output:
                ccys [list[str]]: list of currencies
                res [np.ndarray]: weights array
        """
        pos_value = self.positions_value

        ccys = [
            k for k, p in self._ptf.constituents.items()
            if p.type == 'Cash'
        ]
        aggregated_v = np.zeros(len(ccys))

        for n, uid in enumerate(self._ptf.constituents_uids):
            p = self._ptf.constituents[uid]
            idx = ccys.index(p.currency)
            aggregated_v[idx] += pos_value[n]

        return ccys, aggregated_v / self._curr_tot_val

    def sector_concentration(self) \
            -> tuple[list[str], np.ndarray]:
        """ Returns the weights of the sector exposures at the given date.

            Input:
                date [TyDate]: date at which get exposures

            Output:
                ind [list[str]]: list of sectors
                res [np.ndarray]: weights array
        """
        pos_value = self.positions_value

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

        for n, d in enumerate(data):
            idx = sectors.index(d)
            aggregated_v[idx] += pos_value[n]

        return sectors, aggregated_v / self._curr_tot_val
