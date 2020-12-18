#
# Portfolio class
# Base class for a portfolio
#

from datetime import timedelta
from itertools import groupby

import pandas as pd

from .AggregationMixin import AggregationMixin
from .Asset import Asset
from .AssetFactory import get_af_glob
from nfpy.Financial.EquityMath import sharpe, tev
from nfpy.Financial.Returns import comp_ret
from nfpy.Handlers.CurrencyFactory import get_fx_glob
from nfpy.Portfolio.PortfolioMath import weights, portfolio_value, \
    price_returns, covariance, correlation
from nfpy.Portfolio.Position import Position
from nfpy.Tools.Exceptions import CalendarError


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
        self._fx = get_fx_glob()

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
            res = self._calc_performance()
            self._df["price"] = res
        return res

    def _load_cnsts(self):
        """ Fetch from the database the portfolio constituents. """

        # if inception_date > start load from inception_date
        start_date = self._cal.start
        date = self._inception_date
        flag_snapshot = False

        # If the inception is before the calendar start, search for a snapshot
        # before the calendar start to be used for loading. If no snapshot
        # before start is available, the inception date will be used for loading
        if date < start_date:
            q_date = 'select max(date) from ' + self._CONSTITUENTS_TABLE + \
                     ' where ptf_uid = ? and date <= ?'
            q_data = (self._uid, start_date.to_pydatetime())
            dt = self._db.execute(q_date, q_data).fetchone()
            if dt[0]:
                date = pd.Timestamp(dt[0])
                flag_snapshot = True

        # If the loading date is before the start of the calendar we cannot
        # apply the fx rate while loading the trades. Therefore we quit.
        if date < start_date:
            fmt = '%Y-%m-%d'
            msg = """Calendar staring @ {} but loading required @ {}.
Consider moving back the calendar start date."""
            raise CalendarError(msg.format(start_date.strftime(fmt), date.strftime(fmt)))

        # Initialize needed variables
        uid_list, positions = [], {}
        df = pd.DataFrame(index=self._cal.calendar)

        # Fetch the portfolio snapshot from the DB if a snapshot is available
        if flag_snapshot:
            fields = ('ptf_uid', 'date', 'pos_uid', 'type', 'currency', 'quantity', 'alp')
            q = self._qb.select(self._CONSTITUENTS_TABLE, fields=fields,
                                keys=('ptf_uid', 'date'), order='pos_uid')
            res = self._db.execute(q, (self._uid, date.strftime('%Y-%m-%d'))).fetchall()

            # Create new uid list and constituents dict to ensure any previous
            # non-null value of the variables is overwritten by the new one
            for i, r in enumerate(res):
                pos_uid = r[2]
                dt = pd.Timestamp(r[1])
                pos = Position(pos_uid=pos_uid, date=dt, atype=r[3],
                               currency=r[4], alp=r[6], quantity=r[5])

                uid_list.append(pos_uid)
                positions[pos_uid] = pos
                df.loc[date, pos_uid] = r[5]

        # If we load since inception, create a new position
        else:
            # Create an empty base cash position
            pos_uid = self._currency
            pos = Position(pos_uid=pos_uid, date=date, atype='Cash',
                           currency=self._currency, alp=1., quantity=0)
            uid_list.append(pos_uid)
            positions[pos_uid] = pos
            df.loc[date, pos_uid] = 0

        # Load the trades from the database and apply to positions
        uid_list, positions, df = self._load_trades(date, uid_list,
                                                    positions, df)

        df.fillna(method='ffill', inplace=True)
        df.fillna(0, inplace=True)
        self._cnsts_df = df
        self._date = self._cal.t0
        self._cnsts_uids = uid_list
        self._dict_cnsts = positions

        # Signal constituents loaded
        self._cnsts_loaded = True

    def _load_trades(self, start: pd.Timestamp, uid_list: list,
                     positions: dict, df: pd.DataFrame) -> tuple:
        """ Updates the portfolio positions by adding the pending trades. """
        # This should catch also the trades in the same day
        t0 = self._cal.t0.to_pydatetime() + timedelta(hours=23, minutes=59, seconds=59)
        start = start.to_pydatetime() - timedelta(hours=1)  # days=1)

        # Fetch trades from the database
        q = self._qb.select(self._TRADES_TABLE, rolling=('date',), keys=('ptf_uid',))
        trades = self._db.execute(q, (self._uid, start, t0)).fetchall()

        # If there are no trades just exit
        if not trades:
            return uid_list, positions, df

        af, fx = get_af_glob(), get_fx_glob()
        ccy = self._currency

        # Get the cash position
        cash_pos = positions[ccy]

        # Cycle on trades grouping by date
        # ptf_uid, date, pos_uid, buy_sell, currency, quantity, price, costs, market
        trades.sort(key=lambda f: f[1])
        for date, g in groupby(trades, key=lambda f: f[1]):

            # Sort by date
            gt = list(g)
            dt = pd.to_datetime(date)
            dt = dt.replace(hour=0, minute=0, second=0)

            for t in gt:
                uid = t[2]

                # Update cash positions
                if uid == ccy:
                    sign = 1. if t[3] == 1 else -1.
                    cash_pos.quantity += sign * t[5]
                    df.loc[dt, uid] = cash_pos.quantity

                # Update non cash positions
                else:
                    # Get current values for the position
                    try:
                        v = positions[uid]
                    except KeyError:
                        if fx.is_ccy(uid):
                            atype = 'Cash'
                            alp = 1.
                            currency = uid
                        else:
                            asset = af.get(uid)
                            atype = asset.type
                            alp = .0
                            currency = asset.currency
                        v = Position(pos_uid=uid, date=dt, atype=atype,
                                     currency=currency, alp=alp, quantity=0)
                        uid_list.append(uid)

                    quantity = v.quantity
                    alp = v.alp

                    # We convert the trade price into the position currency
                    # and we update the alp of the position accordingly.
                    fx_rate = 1.
                    if t[4] != v.currency and v.type != 'Cash':
                        fx_obj = fx.get(t[4], v.currency)
                        fx_rate = fx_obj.get(dt)

                    # The rate from the position currency to the base currency
                    # is used to update the base cash position
                    fx_rate_base = 1.
                    if v.currency != ccy:
                        fx_obj_base = fx.get(v.currency, ccy)
                        fx_rate_base = fx_obj_base.get(dt)

                    paid = t[6] * t[5] * fx_rate

                    # BUY trade
                    if t[3] == 1:
                        tot_val = alp * quantity + paid
                        quantity += t[5]
                        cash_pos.quantity -= paid * fx_rate_base
                        alp = tot_val / quantity

                    # SELL trade
                    elif t[3] == 2:
                        quantity -= t[5]
                        cash_pos.quantity += paid * fx_rate_base

                    else:
                        raise ValueError('Buy/Sell flag {} not recognized'.format(t[3]))

                    df.loc[dt, uid] = quantity
                    df.loc[dt, ccy] = cash_pos.quantity

                    if quantity <= 0.:
                        print('pos: {} | value: {:.2f} ==> deleted'.format(uid, quantity))
                        del positions[uid]
                        del uid_list[uid]
                    else:
                        v.quantity = quantity
                        v.alp = alp
                        v.date = dt
                        positions[uid] = v

        cash_pos.date = self._cal.t0
        positions[ccy] = cash_pos
        df.sort_index(inplace=True)

        return uid_list, positions, df

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

        uids, ccy = self._cnsts_uids, self._currency
        pos = self._cnsts_df.values
        dt_df = self._cnsts_df.index.values
        dt, wgt = weights(uids, ccy, dt_df, pos)
        self._weights = pd.DataFrame(wgt, index=dt, columns=uids)

    def _calc_total_value(self) -> pd.Series:
        """ Calculates the times series of the total value of the portfolio. """
        if not self._cnsts_loaded:
            self._load_cnsts()

        uids, ccy = self._cnsts_uids, self._currency
        pos = self._cnsts_df.values
        dt_df = self._cnsts_df.index.values
        dt, tot_val, _ = portfolio_value(uids, ccy, dt_df, pos)
        return pd.Series(tot_val, index=dt)

    def _calc_performance(self) -> pd.Series:
        r = self.returns
        p = comp_ret(r.values, r.index.values, base=1.)
        return pd.Series(p, index=r.index)

    def calc_returns(self) -> pd.Series:
        if not self._cnsts_loaded:
            self._load_cnsts()

        uids, ccy = self._cnsts_uids, self._currency
        pos = self._cnsts_df.values
        dt_pos = self._cnsts_df.index.values
        wgt = self.weights.values
        dt_wgt = self.weights.index.values
        dt, ret = price_returns(uids, ccy, dt_pos, pos, dt_wgt, wgt)
        return pd.Series(ret, index=dt)

    def tev(self, benchmark: Asset, w: int = None) -> pd.Series:
        """ Calculates Tracking Error Volatility of the portfolio against a benchmark

            Input:
                benchmark [Asset]: asset to be used as benchmark
                w [int]: size of the rolling window
        """
        try:
            ret = self._df["TEV"]
        except KeyError:
            r = self.returns
            v = r.values
            dt = r.index.values
            bkr = benchmark.returns.values
            ret = tev(dt, v, bkr, w=w)
            self._df["TEV"] = ret
        return ret

    def sharpe_ratio(self, rf: Asset, w: int = None) -> pd.Series:
        """ Calculates the Sharpe Ratio. """
        try:
            ret = self._df["sharpe"]
        except KeyError:
            r = self.returns
            xc = r.values
            dt = r.index.values
            br = rf.returns.values
            ret = sharpe(dt, xc, br=br, w=w)
            self._df["sharpe"] = ret
        return ret

    def covariance(self) -> pd.DataFrame:
        """ Get the covariance matrix for the underlying constituents. """
        cov, uids = covariance(self._cnsts_uids, self._currency)
        return pd.DataFrame(cov, columns=uids, index=uids)

    def correlation(self) -> pd.DataFrame:
        """ Get the correlation matrix for the underlying constituents. """
        cov, uids = correlation(self._cnsts_uids, self._currency)
        return pd.DataFrame(cov, columns=uids, index=uids)

    def summary(self) -> tuple:
        """ Show the portfolio summary in the portfolio base currency. """
        # Run through positions and collect data for the summary
        data = [(p.uid, p.date.strftime('%Y-%m-%d'), p.type, p.alp, p.quantity,
                 p.alp * p.quantity, p.currency) for p in self._dict_cnsts.values()]

        # Sort accordingly to the key <type, uid>
        data.sort(key=lambda t: (t[2], t[0]))

        fields = ('uid', 'date', 'type', 'alp', 'quantity', 'value', 'currency')
        return fields, data
