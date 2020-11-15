#
# Portfolio class
# Base class for a portfolio
#

from datetime import timedelta
from itertools import groupby

import pandas as pd

from nfpy.Assets.AggregationMixin import AggregationMixin
from nfpy.Assets.Asset import Asset
from nfpy.Financial.EquityMath import sharpe, tev
from nfpy.Handlers.AssetFactory import get_af_glob
from nfpy.Handlers.Calendar import get_calendar_glob
from nfpy.Handlers.CurrencyFactory import get_fx_glob  # , DummyConversion
from nfpy.Portfolio.PortfolioMath import weights, portfolio_value, \
    price_returns, covariance
from nfpy.Portfolio.Position import Position


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

    def _load_cnsts(self):
        """ Fetch from the database the portfolio constituents. """

        # if inception_date > start load from inception_date
        start_date = self._cal.start
        date = self._inception_date
        flag_snapshot = False

        if date < start_date:
            # search for newest snapshot before start_date
            q_date = 'select max(date) from ' + self._CONSTITUENTS_TABLE + \
                     ' where ptf_uid = ? and date <= ?'
            q_data = (self._uid, start_date.to_pydatetime())
            dt = self._db.execute(q_date, q_data).fetchone()
            if dt:
                date = dt[0]
                flag_snapshot = True

        # Initialize needed variables
        uid_list, positions = [], {}
        df = pd.DataFrame(index=get_calendar_glob().calendar)

        # Fetch the portfolio snapshot from the DB if a snapshot is available
        if flag_snapshot:
            fields = ('ptf_uid', 'date', 'pos_uid', 'type', 'quantity', 'alp')
            q = self._qb.select(self._CONSTITUENTS_TABLE, fields=fields,
                                keys=('ptf_uid', 'date'), order='pos_uid')
            res = self._db.execute(q, (self._uid, date)).fetchall()

            # Create new uid list and constituents dict to ensure any previous
            # non-null value of the variables is overwritten by the new one
            for i, r in enumerate(res):
                pos_uid = r[2]
                dt = pd.Timestamp(r[1])
                pos = Position(pos_uid=pos_uid, date=dt, atype=r[3],
                               alp=r[5], quantity=r[4])

                uid_list.append(pos_uid)
                positions[pos_uid] = pos
                df.loc[start_date, pos_uid] = r[4]

        else:
            # Create an empty base cash position
            pos_uid = self._currency
            pos = Position(pos_uid=pos_uid, atype='Cash', alp=1.,
                           date=date.strftime('%Y-%m-%d'), quantity=.0)
            uid_list.append(pos_uid)
            positions[pos_uid] = pos
            df.loc[date, pos_uid] = 0

        # Load the trades from the database and apply to positions
        uid_list, positions, df = self._load_trades(start_date, uid_list,
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
        t0 = self._cal.t0.to_pydatetime() + \
             timedelta(hours=23, minutes=59, seconds=59)
        start = start.to_pydatetime()

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
                        asset = af.get(uid)
                        v = Position(pos_uid=uid, date=dt, atype=asset.type,
                                     alp=.0, quantity=0)
                        uid_list.append(uid)

                    quantity = v.quantity
                    alp = v.alp

                    # We convert the trade price into the position currency
                    # and we update the alp of the position accordingly.
                    fx_rate = 1.
                    if t[4] != ccy and v.type != 'Cash':
                        fx_obj = fx.get(t[4], ccy)
                        fx_rate = fx_obj.get(dt)

                    paid = t[6] * t[5] * fx_rate

                    # BUY trade
                    if t[3] == 1:
                        tot_val = alp * quantity + paid
                        quantity += t[5]
                        cash_pos.quantity -= paid
                        alp = tot_val / quantity

                    # SELL trade
                    elif t[3] == 2:
                        quantity -= t[5]
                        cash_pos.quantity += paid

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

        return uid_list, positions, df

    def _write_cnsts(self):
        """ Writes to the database the constituents. """
        fields = ('uid', 'date', 'alp', 'quantity', 'type')
        data = []
        for c in self._dict_cnsts.values():
            data.append((getattr(c, k) for k in fields))

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
        wgt, _ = weights(uids, ccy, pos)

        cal = get_calendar_glob().calendar
        self._weights = pd.DataFrame(wgt, index=cal, columns=self._cnsts_uids)

    def _calc_total_value(self):
        """ Calculates the times series of the total value of the portfolio. """
        if not self._cnsts_loaded:
            self._load_cnsts()

        uids, ccy = self._cnsts_uids, self._currency
        pos = self._cnsts_df.values
        tot_val, _ = portfolio_value(uids, ccy, pos)
        return tot_val

    def calc_returns(self):
        if not self._cnsts_loaded:
            self._load_cnsts()

        uids, ccy = self._cnsts_uids, self._currency
        pos = self._cnsts_df.values
        wgt = self.weights.values
        return price_returns(uids, ccy, pos, wgt)

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
            ret = tev(dt, v, bkr, w)
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
            ret = sharpe(dt, xc, br, w)
            self._df["sharpe"] = ret
        return ret

    def covariance(self):
        """ Get the covariance matrix for the underlying constituents. """
        cov, uids = covariance(self._cnsts_uids, self._currency)
        return pd.DataFrame(cov, columns=uids, index=uids)

################################################################################

# def _calc_cnsts_returns(self):
#     """ Create the matrix of returns from constituents """
#     if not self._cnsts_loaded:
#         self._load_cnsts()
#
#     # Here we must cycle on the ordered sequence, not directly on the
#     # dictionary, to enforce the order in the final dataframe
#     for uid in self._cnsts_uids:
#         pos = self._dict_cnsts[uid]
#         r = pos.obj.returns
#         ccy = pos.obj.currency
#         if ccy != self._currency:
#             fx = self._fx.get(ccy, self._currency)
#             r = r + fx.returns + r * fx.returns
#         self._cnsts_df[uid] = r
#
# def expected_constituents_return(self, start: pd.Timestamp = None,
#                                  end: pd.Timestamp = None) -> np.array:
#     """ Expected return of the constituent assets. """
#     if self._cnsts_df.empty:
#         self._calc_cnsts_returns()
#
#     df = self._cnsts_df
#     ts, dt = df.values, df.index.values
#     return expct_ret(ts, dt, start=start, end=end, is_log=False)
#
# def constituents_volatility(self, start: pd.Timestamp = None,
#                             end: pd.Timestamp = None) -> np.array:
#     """ Volatility of the return of the constituent assets. """
#     if self._cnsts_df.empty:
#         self._calc_cnsts_returns()
#
#     df = self._cnsts_df
#     ts, dt = df.values, df.index.values
#     ts, _ = trim_ts(ts, dt, start=start, end=end)
#     return np.nanstd(ts, axis=0)
#
# def _calc_variance(self):
#     """ Calculates the portfolio variance given constituents covariance and
#         assets weights.
#     """
#     wgt = self.weights.values
#     cov = self.covariance.values
#     self._var = float(np.dot(wgt.T, np.dot(cov, wgt)))
