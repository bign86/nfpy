#
# Portfolio class
# Base class for a portfolio
#

import warnings
# from time import process_time, process_time_ns

import numpy as np
import pandas as pd

from nfpy.Assets.AggregationMixin import AggregationMixin
from nfpy.Assets.Asset import Asset
from nfpy.Financial.Returns import expct_ret
from nfpy.Financial.TSMath import sharpe, tev
from nfpy.Handlers.AssetFactory import get_af_glob
from nfpy.Handlers.CurrencyFactory import get_fx_glob
from nfpy.Portfolio.Position import Position
from nfpy.Tools.Exceptions import MissingDataWarn
from nfpy.Tools.TSUtils import trim_ts


class Portfolio(AggregationMixin, Asset):
    """ Base class to hold information on a single portfolio """

    _TYPE = 'Portfolio'
    _BASE_TABLE = 'Portfolio'
    _CONSTITUENTS_TABLE = 'PortfolioPositions'
    _TS_TABLE = 'PortfolioTS'  # NOTE: not in use
    _TS_ROLL_KEY_LIST = ['date']  # NOTE: not in use

    def __init__(self, uid: str, date: pd.Timestamp = None):
        super().__init__(uid)
        # self._cal = get_calendar_glob()
        self._fx = get_fx_glob()

        self._weights = pd.DataFrame()
        self._cov = pd.DataFrame()
        self._var = pd.DataFrame()
        self._date = date
        self._tot_value = None
        self._base_cash = None

    @property
    def base_cash_pos(self) -> Position:
        return self._base_cash

    @property
    def date(self) -> pd.Timestamp:
        return self._date

    @date.setter
    def date(self, v):
        if not isinstance(v, pd.Timestamp):
            v = pd.Timestamp(v)
        self._date = v

    @date.deleter
    def date(self):
        self._date = None

    @property
    def weights(self) -> pd.DataFrame:
        """ Return the weights """
        if self._weights.empty:
            self._calc_weights()
        return self._weights

    @weights.deleter
    def weights(self):
        self._weights = pd.DataFrame()

    @property
    def covariance(self):
        if self._cov.empty:
            self._calc_covariance()
        return self._cov

    @property
    def variance(self):
        if self._var.empty:
            self._calc_variance()
        return self._var

    def _load_cnsts(self):
        """ Fetch from the database the portfolio constituents """

        # Get the date interval to search the portfolio image on
        end_date = self._cal.t0.to_pydatetime()
        start_date = self._cal.start.to_pydatetime()
        q_date = 'select max(date) from ' + self._CONSTITUENTS_TABLE + \
                 ' where ptf_uid = ? and date <= ?'

        # Search the date of the last portfolio snapshot available in DB
        # lesser equal the calendar t0
        date = self._db.execute(q_date, (self._uid, end_date)).fetchone()[0]
        if date is None:
            warnings.warn("No constituents for {} between {} and {}"
                          .format(self._uid, start_date, end_date), MissingDataWarn)
            self._cnsts_loaded = False

        # Fetch the portfolio snapshot from the DB
        fields = ('ptf_uid', 'date', 'pos_uid', 'type', 'currency', 'quantity', 'alp')
        q = self._qb.select(self._CONSTITUENTS_TABLE, fields=fields,
                            keys=('ptf_uid', 'date'), order='pos_uid')
        res = self._db.execute(q, (self._uid, date)).fetchall()

        # Transform into pd.Timestamp for later use and save in self._date
        date = pd.to_datetime(date, format='%Y-%m-%d')

        # Create new uid list and constituents dict to ensure any previous
        # non-null value of the variables is overwritten by the new one
        uid, cnsts_dict = [], {}
        af = get_af_glob()
        for i, r in enumerate(res):
            pos_uid = r[2]
            if r[3] == 'Cash':
                # If the position is in cash convert the amount to base ccy
                a_obj = self._fx.get(r[4], self._currency)
                # If the position in in the base ccy, check that the average
                # price per unit is set to 1 for consistency
                if pos_uid == self._currency:
                    assert r[6] == 1.
            else:
                a_obj = af.get(pos_uid)

            pos = Position(pos_uid=pos_uid, date=r[1], atype=r[3],
                           currency=r[4], alp=r[6], quantity=r[5], obj=a_obj)
            if pos_uid == self._currency:
                self._base_cash = pos
            else:
                uid.append(pos_uid)
                cnsts_dict[pos_uid] = pos

        # Consistency check
        assert self._base_cash is not None

        self._date = date
        self._cnsts_uids = uid
        self._dict_cnsts = cnsts_dict
        self._weights = pd.DataFrame(index=uid)
        self._cov = pd.DataFrame(index=uid)

        # Signal constituents loaded
        self._cnsts_loaded = True

    def _write_cnsts(self):
        """ Writes to the database the constituents. """

        # Run on the positions and convert back from the general base currency
        # used in the code to the portfolio one used for saving
        data = []
        for c in self._dict_cnsts.values():
            # if (c.type == 'Cash') and (c.uid == self._currency):
            #     assert c.alp == 1.
            data.append((self._uid, self.date.to_pydatetime(), c.uid, c.uid,
                         c.type, c.currency, c.quantity, c.alp))

        c = self._base_cash
        assert c.alp == 1.
        data.append((self._uid, self.date.to_pydatetime(), c.uid, c.uid,
                     c.type, c.currency, c.quantity, c.alp))

        q = self._qb.merge(self._CONSTITUENTS_TABLE)
        self._db.executemany(q, data, commit=True)

    def _get_cnsts_returns(self):
        """ Create the matrix of returns from constituents """
        if not self._cnsts_loaded:
            self._load_cnsts()

        # FIXME: move calculation outside portfolio class
        # Here we must cycle on the ordered sequence, not directly on the
        # dictionary, to enforce the order in the final dataframe
        for uid in self._cnsts_uids:
            pos = self._dict_cnsts[uid]
            r = pos.obj.returns
            ccy = pos.obj.currency
            if ccy != self._currency:
                fx = self._fx.get(ccy, self._currency)
                r = r + fx.returns + r * fx.returns
            self._cnsts_df[uid] = r

    def calc_returns(self):
        """ Trigger the calculation of returns. Overrides the one in Asset. """
        if self._cnsts_df.empty:
            self._get_cnsts_returns()
        return self._cnsts_df.dot(self.weights)

    def calc_log_returns(self):
        raise NotImplementedError("Log returns not available for portfolios!")

    def expected_constituents_return(self, start: pd.Timestamp = None,
                                     end: pd.Timestamp = None) -> np.array:
        """ Expected return of the constituent assets. """
        if self._cnsts_df.empty:
            self._get_cnsts_returns()

        df = self._cnsts_df
        ts, dt = df.values, df.index.values
        return expct_ret(ts, dt, start=start, end=end, is_log=False)

    def constituents_volatility(self, start: pd.Timestamp = None,
                                end: pd.Timestamp = None) -> np.array:
        """ Volatility of the return of the constituent assets. """
        if self._cnsts_df.empty:
            self._get_cnsts_returns()

        df = self._cnsts_df
        ts, dt = df.values, df.index.values
        ts, _ = trim_ts(ts, dt, start=start, end=end)
        return np.nanstd(ts, axis=0)
        # return expct_ret(ts, dt, start=start, end=end, is_log=False)

    def _calc_weights(self):
        """ Calculates constituents weights starting from portfolio positions. """
        # FIXME: move calculation outside portfolio class
        if not self._cnsts_loaded:
            self._load_cnsts()

        t0 = self._cal.t0
        wgt = np.empty(self.num_constituents)
        for i, uid in enumerate(self._cnsts_uids):
            pos = self._dict_cnsts[uid]
            ccy = pos.obj.currency
            fx = self._fx.get(ccy, self._currency).get(t0)
            wgt_ = pos.quantity * fx
            if pos.type != 'Cash':
                wgt_ = wgt_ * pos.obj.prices.at[t0]
            wgt[i] = wgt_

        # Normalize weights
        base_cash_wgt = self._base_cash.quantity
        wgt = wgt / (np.sum(wgt) + base_cash_wgt)
        self._weights["weight"] = pd.Series(wgt, index=self._cnsts_uids)

    def _calc_covariance(self):
        """ Get the covariance matrix for the underlying constituents. """
        if self._cnsts_df.empty:
            self._get_cnsts_returns()

        # The pure numpy version is slower on big matrices
        self._cov = self._cnsts_df.cov()

    def _calc_variance(self):
        """ Calculates the portfolio variance given constituents covariance and
            assets weights.
        """
        # FIXME: move calculation outside portfolio class
        wgt = self.weights.values
        cov = self.covariance.values
        self._var = float(np.dot(wgt.T, np.dot(cov, wgt)))

    # def _calc_total_value(self):
    #     """ Calculate the total value of the portfolio summing over the single
    #         positions. The value is calculated at the update date of the
    #         portfolio.
    #     """
    #     tot_value = self._base_cash.quantity
    #     for p in self.constituents.values():
    #         # if (p.type == 'Cash') and (p.uid == self._fx.base_ccy):
    #         #     price = 1.
    #         # else:
    #         #     price = p.obj.prices[self._date]
    #         idx = p.obj.prices.loc[:self._date].last_valid_index()
    #         tot_value += p.quantity * p.obj.prices.at[idx]
    #         # tot_value = tot_value + new_v
    #     self._tot_value = tot_value

    ################################################################################

    def tev(self, benchmark: Asset, w: int = None) -> pd.Series:
        """ Calculates Tracking Error Volatility of the portfolio against a benchmark

            Input:
                benchmark [Asset]: asset to be used as benchmark
                w [int]: size of the rolling window
        """
        try:
            ret = self._df["TEV"]
        except KeyError:
            ret = tev(self.returns, benchmark.returns, w)
            self._df["TEV"] = ret
        return ret

    def sharpe_ratio(self, rf: Asset, window: int = None) -> pd.Series:
        """ Calculates the Sharpe Ratio. """
        try:
            ret = self._df["sharpe"]
        except KeyError:
            ret = sharpe(self.returns, rf.returns, window)
            self._df["sharpe"] = ret
        return ret
