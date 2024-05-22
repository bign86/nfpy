#
# Portfolio class
# Base class for a portfolio
#

from datetime import timedelta

import numpy as np
import pandas as pd

import nfpy.IO.Utilities as Ut

from .AggregationMixin import AggregationMixin
from .Asset import Asset
from .Position import Position


class PortfolioTargets(object):

    def __init__(self):
        self._industry = None
        self._sector = None
        self._geography = None


class Portfolio(AggregationMixin, Asset):
    """ Base class to hold information on a single portfolio """

    _TYPE = 'Portfolio'
    _BASE_TABLE = 'Portfolio'
    _CONSTITUENTS_TABLE = 'PortfolioPositions'
    _TRADES_TABLE = 'Trades'

    def __init__(self, uid: str):
        super().__init__(uid)

        self.weights = None
        self._tot_curr_value = None
        self._inception_date = None
        self._last_position_date = None
        self._benchmark = None

        self._is_history_loaded = False

        self._divs_received = pd.DataFrame(index=self._cal.calendar)
        self._cash_ops = pd.DataFrame([])

    @property
    def benchmark(self) -> str:
        return self._benchmark

    @benchmark.setter
    def benchmark(self, v: str) -> None:
        self._benchmark = v

    def calc_log_returns(self) -> None:
        raise NotImplementedError("Portfolio(): Log returns not available for portfolios!")

    @property
    def cash_ops(self) -> pd.DataFrame:
        return self._cash_ops

    @property
    def dividends_received(self) -> pd.DataFrame:
        return self._divs_received

    @property
    def inception_date(self) -> pd.Timestamp:
        return self._inception_date

    @inception_date.setter
    def inception_date(self, v: str) -> None:
        self._inception_date = pd.Timestamp(v)

    def load(self) -> None:
        super(Portfolio, self).load()

    @property
    def performance(self, *args):
        raise NotImplementedError("Portfolio(): performance() not implemented!")

    @property
    def position_age(self) -> int:
        return int(self._cal.t0.asm8 - self._last_position_date)

    @property
    def positions_hist(self) -> pd.DataFrame:
        if not self._is_history_loaded:
            raise ValueError('Portfolio(): history not loaded. Use the PortfolioEngine() fot this.')
        return self._cnsts_df

    def _load_cnsts(self) -> None:
        """ Fetch from the database the portfolio constituents. """

        # Get dates
        start_date = self._cal.start
        inception = self._inception_date

        # If the portfolio does not exist yet return an error
        if inception > self._cal.t0:
            msg = f'Portfolio(): inception date {inception} is past the t0 of calendar'
            raise ValueError(msg)

        last_pos_dt = self._db.execute(
            f'select max(date) from {self._CONSTITUENTS_TABLE}'
            f' where ptf_uid = ? and date >= ? and date <= ?',
            (self._uid, inception, self._cal.t0)
        ).fetchone()

        # If there are no positions, we create the base currency position
        if last_pos_dt is None:
            Ut.print_wrn(Warning('Portfolio(): no snapshots found'))

            date = inception \
                if inception > start_date \
                else start_date

            ccy = self._currency
            base_ccy_pos = Position(
                pos_uid=ccy, date=date, atype='Cash',
                currency=ccy, alp=1., quantity=0
            )

            self._dict_cnsts = {ccy: base_ccy_pos}
            self._last_position_date = np.datetime64(date.asm8)

        # If positions are found load them
        else:
            positions = self._db.execute(
                self._qb.select(
                    self._CONSTITUENTS_TABLE,
                    keys=('ptf_uid', 'date'),
                    order='pos_uid'
                ),
                (self._uid, last_pos_dt[0])
            ).fetchall()

            uids = []
            for pos in positions:
                pos_dt = pd.Timestamp(pos[1])
                pos_uid = pos[2]

                p = Position(
                    pos_uid=pos_uid, date=pos_dt, atype=pos[3],
                    currency=pos[4], alp=pos[6], quantity=pos[5]
                )

                uids.append(pos_uid)
                self._dict_cnsts[pos_uid] = p

            uids.remove(self._currency)
            self._cnsts_uids = uids
            self._last_position_date = np.datetime64(last_pos_dt[0])
            self._cnsts_loaded = True

    def _load_pos_hist(self) -> list:
        """ Fetch from the database the history of portfolio positions. """
        params = (
            self._uid,
            self._inception_date.to_pydatetime() - timedelta(hours=1),  # days=1)
            self._cal.t0.to_pydatetime() + timedelta(hours=23, minutes=59, seconds=59),
        )
        q = self._qb.select(self._CONSTITUENTS_TABLE, rolling=('date',), keys=('ptf_uid',))
        return self._db.execute(q, params).fetchall()

    def _load_trades(self) -> list:
        """ Fetch from the database the history of trades. """
        params = (
            self._uid,
            self._inception_date.to_pydatetime() - timedelta(hours=1),  # days=1)
            self._cal.t0.to_pydatetime() + timedelta(hours=23, minutes=59, seconds=59),
        )
        q = self._qb.select(self._TRADES_TABLE, rolling=('date',), keys=('ptf_uid',))
        return self._db.execute(q, params).fetchall()

    def _write_cnsts(self) -> None:
        """ Writes to the database the constituents. """
        fields = tuple(self._qb.get_fields(self._CONSTITUENTS_TABLE))
        curr_date = self._cal.t0.to_pydatetime().date()
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

        self._db.executemany(
            self._qb.merge(self._CONSTITUENTS_TABLE, ins_fields=fields),
            data, commit=True
        )
