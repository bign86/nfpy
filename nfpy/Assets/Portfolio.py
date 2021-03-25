#
# Portfolio class
# Base class for a portfolio
#

from bisect import bisect_left
from datetime import (datetime, timedelta)
from itertools import groupby
import pandas as pd

import nfpy.Financial as Fin
from nfpy.Tools import Exceptions as Ex

from .AggregationMixin import AggregationMixin
from .Asset import Asset
from .AssetFactory import get_af_glob
from .Position import Position


class Portfolio(AggregationMixin, Asset):
    """ Base class to hold information on a single portfolio """

    _TYPE = 'Portfolio'
    _BASE_TABLE = 'Portfolio'
    _CONSTITUENTS_TABLE = 'PortfolioPositions'
    _TS_TABLE = 'PortfolioTS'  # NOTE: not in use
    _TS_ROLL_KEY_LIST = ['date']  # NOTE: not in use
    _POSITIONS_TABLE = 'PortfolioPositions'
    _TRADES_TABLE = 'Trades'

    def __init__(self, uid: str, date: pd.Timestamp = None):
        super().__init__(uid)
        # self._fx = Fin.get_fx_glob()

        self._weights = pd.DataFrame()
        self._date = date
        self._tot_value = None
        self._inception_date = None

    @property
    def date(self) -> pd.Timestamp:
        return self._date

    @property
    def inception_date(self) -> pd.Timestamp:
        return self._inception_date

    @inception_date.setter
    def inception_date(self, v: str):
        self._inception_date = pd.Timestamp(v)

    @property
    def weights(self) -> pd.DataFrame:
        """ Return the weights. """
        if self._weights.empty:
            self._calc_weights()
        return self._weights

    @property
    def total_value(self) -> pd.Series:
        """ Return the total value series of the portfolio. """
        try:
            res = self._df["tot_value"]
        except KeyError:
            res = self._calc_total_value()
            self._df["tot_value"] = res
        return res

    @property
    def prices(self) -> pd.Series:
        """ Calculates the performance series for the portfolio. """
        try:
            res = self._df["price"]
        except KeyError:
            res = self.performance()
            self._df["price"] = res
        return res

    def _load_cnsts(self):
        """ Fetch from the database the portfolio constituents. """

        # If inception_date > start load from inception_date
        start_date = self._cal.start
        date = self._inception_date
        flag_snapshot = False

        # If the inception is before the calendar start, search for a snapshot
        # before the calendar start to be used for loading. If no snapshot
        # before start is available, the inception date will be used for loading
        if date < start_date:
            query_snap = 'select distinct date from ' + self._CONSTITUENTS_TABLE + \
                         ' where ptf_uid = ? order by date'
            dt = self._db.execute(query_snap, (self._uid,)).fetchall()

            dt = [datetime.strptime(d[0], '%Y-%m-%d') for d in dt]
            dt = [date.to_pydatetime()] + dt
            idx = bisect_left(dt, start_date)

            # If the required loading date is before the start of the calendar
            # we cannot apply the fx rate while loading the trades thus we quit
            if idx == len(dt):
                fmt = '%Y-%m-%d'
                msg = """Calendar starting @ {} but loading required @ {}.
Consider moving back the calendar start date."""
                raise Ex.CalendarError(msg.format(start_date.strftime(fmt),
                                                  dt[-1].strftime(fmt)))

            # If a snapshot in the future is available just use it
            date = pd.Timestamp(dt[idx])
            flag_snapshot = True

        # Initialize needed variables
        positions = {}
        df = pd.DataFrame(index=self._cal.calendar)

        # Fetch the portfolio snapshot from the DB if a snapshot is available
        if flag_snapshot:
            q = self._qb.select(self._CONSTITUENTS_TABLE,
                                keys=('ptf_uid', 'date'), order='pos_uid')
            res = self._db.execute(q, (self._uid, date.strftime('%Y-%m-%d'))).fetchall()

            # Create new uid list and constituents dict to ensure any previous
            # non-null value of the variables is overwritten by the new one
            for i, r in enumerate(res):
                pos_uid = r[2]
                dt = pd.Timestamp(r[1])
                pos = Position(pos_uid=pos_uid, date=dt, atype=r[3],
                               currency=r[4], alp=r[6], quantity=r[5])

                positions[pos_uid] = pos
                df.loc[date, pos_uid] = r[5]

        # If we load since inception, create a new position
        else:
            # Create an empty base cash position
            pos_uid = self._currency
            pos = Position(pos_uid=pos_uid, date=date, atype='Cash',
                           currency=self._currency, alp=1., quantity=0)
            positions[pos_uid] = pos
            df.loc[date, pos_uid] = 0

        # Load the trades from the database and apply to positions
        positions, df = self._load_trades(date, positions, df)

        df.fillna(method='ffill', inplace=True)
        df.fillna(0, inplace=True)
        self._cnsts_df = df
        self._date = self._cal.t0
        self._cnsts_uids = df.columns.tolist()
        self._dict_cnsts = positions

        # Signal constituents loaded
        self._cnsts_loaded = True

    def _load_trades(self, start: pd.Timestamp, positions: dict,
                     df: pd.DataFrame) -> tuple:
        """ Updates the portfolio positions by adding the pending trades. """
        # This should catch also the trades in the same day
        t0 = self._cal.t0.to_pydatetime() + timedelta(hours=23, minutes=59, seconds=59)
        start = start.to_pydatetime() - timedelta(hours=1)  # days=1)

        # Fetch trades from the database
        q = self._qb.select(self._TRADES_TABLE, rolling=('date',), keys=('ptf_uid',))
        trades = self._db.execute(q, (self._uid, start, t0)).fetchall()

        # If there are no trades just exit
        if not trades:
            return positions, df

        af, fx = get_af_glob(), Fin.get_fx_glob()

        # Cycle on trades grouping by date
        trades.sort(key=lambda f: f[1])
        for date, g in groupby(trades, key=lambda f: f[1]):

            # Sort by date
            gt = list(g)
            dt = pd.to_datetime(date)
            dt = dt.replace(hour=0, minute=0, second=0)

            for t in gt:
                uid, trade_ccy = t[2], t[4]
                traded_q = t[5] if t[3] == 1 else -t[5]
                traded_cash = t[6] * traded_q

                # Get the asset position
                try:
                    v = positions[uid]
                except KeyError:
                    if fx.is_ccy(uid):
                        v = Position(pos_uid=uid, date=dt,
                                     atype='Cash', currency=uid,
                                     alp=1., quantity=0)
                    else:
                        asset = af.get(uid)
                        v = Position(pos_uid=uid, date=dt,
                                     atype=asset.type,
                                     currency=asset.currency,
                                     alp=.0, quantity=0)
                    positions[uid] = v

                # Get the currency position
                if (trade_ccy is not None) & (trade_ccy != uid):
                    try:
                        cash = positions[trade_ccy]
                    except KeyError:
                        cash = Position(pos_uid=trade_ccy, date=dt,
                                        atype='Cash', currency=trade_ccy,
                                        alp=1., quantity=0)
                        positions[trade_ccy] = cash
                else:
                    cash = None

                # Update any cash position
                if fx.is_ccy(uid):
                    v.quantity += traded_q
                    v.date = dt
                    df.loc[dt, uid] = v.quantity

                # Update non-cash positions
                else:
                    # Calculate traded money and new quantity
                    old_quantity = v.quantity
                    v.quantity += traded_q

                    # We convert the trade price into the position currency
                    # and we update the alp of the position accordingly.    
                    pos_fx_rate = 1.
                    if trade_ccy != v.currency:
                        fx_obj = fx.get(trade_ccy, v.currency)
                        pos_fx_rate = fx_obj.get(dt)

                    # Calculate the average cost of the instrument considering
                    # whether we buy/sell/short sell/short cover and the
                    # starting quantity.
                    if v.quantity < 0:
                        v.alp = .0
                    elif old_quantity < 0:
                        v.alp = t[6] * pos_fx_rate
                    elif traded_q > 0:
                        v.alp = (old_quantity * v.alp +
                                 traded_cash * pos_fx_rate) / v.quantity
                    # else: traded_q < 0 => v.alp = old_alp. We skip this case

                    # Update positions
                    v.date = dt
                    df.loc[dt, uid] = v.quantity

                    if v.quantity == 0.:
                        print('pos: {} | quantity: {:.2f} ==> deleted'
                              .format(uid, v.quantity))
                        del positions[uid]

                # Update cash position
                if cash is not None:
                    cash.quantity -= traded_cash
                    cash.date = dt
                    df.loc[dt, trade_ccy] = cash.quantity

        positions[self._currency].date = self._cal.t0
        df.sort_index(inplace=True)

        return positions, df

    def _write_cnsts(self):
        """ Writes to the database the constituents. """
        fields = tuple(self._qb.get_fields(self._CONSTITUENTS_TABLE))
        curr_date = self._date.to_pydatetime().date()
        data = []
        for c in self._dict_cnsts.values():
            d = []
            for i, k in enumerate(fields):
                if k == 'ptf_uid':
                    v = self._uid
                elif k == 'date':
                    v = curr_date
                elif k in ('pos_uid', 'asset_uid'):
                    v = getattr(c, 'uid')
                else:
                    v = getattr(c, k)
                d.append(v)
            data.append(tuple(d))

        q = self._qb.merge(self._CONSTITUENTS_TABLE, ins_fields=fields)
        self._db.executemany(q, data, commit=True)

    def calc_log_returns(self):
        raise NotImplementedError("Log returns not available for portfolios!")

    def _calc_weights(self):
        """ Calculates constituents weights starting from portfolio positions. """
        if not self._cnsts_loaded:
            self._load_cnsts()

        pos = self._cnsts_df
        uids = self._cnsts_uids
        dt, wgt = Fin.weights(uids, self._currency,
                              pos.index.values, pos.values)
        self._weights = pd.DataFrame(wgt, index=dt, columns=uids)

    def _calc_total_value(self) -> pd.Series:
        """ Calculates the times series of the total value of the portfolio. """
        if not self._cnsts_loaded:
            self._load_cnsts()

        pos = self._cnsts_df
        dt, tot_val, _ = Fin.ptf_value(self._cnsts_uids, self._currency,
                                       pos.index.values, pos.values)
        return pd.Series(tot_val, index=dt)

    def positions_value(self) -> pd.DataFrame:
        """ Calculates the times series of the value of each position in base
            currency. The sum across positions at each date is the portfolio
            total value at that date.
        """
        if not self._cnsts_loaded:
            self._load_cnsts()

        pos = self._cnsts_df
        dt, _, pos_val = Fin.ptf_value(self._cnsts_uids, self._currency,
                                       pos.index.values, pos.values)
        return pd.DataFrame(pos_val, columns=self._cnsts_uids, index=dt)

    def calc_returns(self) -> pd.Series:
        if not self._cnsts_loaded:
            self._load_cnsts()

        pos = self._cnsts_df
        wgt = self.weights
        dt, ret = Fin.price_returns(self._cnsts_uids, self._currency,
                                    pos.index.values, pos.values,
                                    wgt.index.values, wgt.values)
        return pd.Series(ret, index=dt)

    def tev(self, benchmark: Asset, w: int = None) -> pd.Series:
        """ Calculates Tracking Error Volatility of the portfolio against a benchmark

            Input:
                benchmark [Asset]: asset to be used as benchmark
                w [int]: size of the rolling window
        """
        r = self.returns
        ret = Fin.tev(r.index.values, r.values,
                      benchmark.returns.values, w=w)
        return pd.Series(ret, index=r.index)

    def sharpe_ratio(self, rf: Asset, w: int = None) -> pd.Series:
        """ Calculates the Sharpe Ratio. """
        r = self.returns
        ret = Fin.sharpe(r.index.values, r.values,
                         br=rf.returns.values, w=w)
        return pd.Series(ret, index=r.index)

    def covariance(self) -> pd.DataFrame:
        """ Get the covariance matrix for the underlying constituents. """
        cov, uids = Fin.ptf_cov(self._cnsts_uids, self._currency)
        return pd.DataFrame(cov, columns=uids, index=uids)

    def correlation(self) -> pd.DataFrame:
        """ Get the correlation matrix for the underlying constituents. """
        cov, uids = Fin.ptf_corr(self._cnsts_uids, self._currency)
        return pd.DataFrame(cov, columns=uids, index=uids)

    def summary(self) -> dict:
        """ Show the portfolio summary in the portfolio base currency. """
        # Run through positions and collect data for the summary
        pos_value = self.positions_value().loc[self._date]
        tot_value = pos_value.sum()

        data = []
        for k, p in self._dict_cnsts.items():
            val = float(pos_value[k])
            cost = p.alp * p.quantity
            t = (p.type, p.uid, p.date.strftime('%Y-%m-%d'), p.currency,
                 p.alp, p.quantity, cost, val)
            data.append(t)

        # Sort accordingly to the key <type, uid>
        data.sort(key=lambda _t: (_t[0], _t[1]))
        fields = ('type', 'uid', 'date', 'currency', 'alp', 'quantity',
                  'cost (FX)', 'value ({})'.format(self._currency))
        cnsts = pd.DataFrame(data, columns=fields)

        return {
            'uid': self._uid, 'currency': self._currency, 'date': self._date,
            'inception': self._inception_date, 'tot_value': tot_value,
            'constituents_data': cnsts,
        }
