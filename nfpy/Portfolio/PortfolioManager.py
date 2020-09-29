#
# Portfolio Manager class
# Creates/Deletes trades and updates positions
#

from datetime import timedelta, datetime
from itertools import groupby
from typing import Union

import pandas as pd

from nfpy.Assets import Portfolio
from nfpy.DB.DB import get_db_glob
from nfpy.Handlers.AssetFactory import get_af_glob
from nfpy.Handlers.Calendar import get_calendar_glob, date_2_datetime
from nfpy.Handlers.CurrencyFactory import get_fx_glob
from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Portfolio.Position import Position
from nfpy.Tools.Exceptions import MissingData


class PortfolioManager(object):
    """ Position class, contains the information on a single portfolio position. """

    _POSITIONS_TABLE = 'PortfolioPositions'
    _TRADES_TABLE = 'Trades'

    def __init__(self):
        self._af = get_af_glob()
        self._fx = get_fx_glob()
        self._db = get_db_glob()
        self._qb = get_qb_glob()
        self._cal = get_calendar_glob()

    def new_trade(self, ptf_uid: str, date: Union[str, datetime, pd.Timestamp],
                  pos_uid: str, buy_sell: int, currency: str, quantity: float, price: float,
                  costs: float = None, market: str = None, date_fmt: str = '%Y-%m-%d %H:%M:%S'):
        date = date_2_datetime(date, fmt=date_fmt)
        q = self._qb.insert(self._TRADES_TABLE)
        data = (ptf_uid, date, pos_uid, buy_sell, currency, quantity, price, costs, market)
        self._db.execute(q, data, commit=True)

    def delete_trade(self, ptf_uid: str, date: pd.Timestamp, pos_uid: str):
        q = self._qb.delete(self._TRADES_TABLE)
        data = (ptf_uid, date, pos_uid)
        self._db.execute(q, data, commit=True)

    def new_position(self, pos_uid: str, date: pd.Timestamp, atype: str,
                     currency: str, alp: float, quantity: float, base_ccy: str) -> Position:
        if atype == 'Cash':
            a_obj = self._fx.get(currency, base_ccy)
        else:
            a_obj = self._af.get(pos_uid)
        return Position(pos_uid, date, atype, currency, alp, quantity, a_obj)

    def update(self, ptf: Portfolio):
        """ Updates the portfolio positions by adding the pending trades. """
        # This should catch also the trades in the same day
        end_time = self._cal.t0.to_pydatetime() + \
                   timedelta(hours=23, minutes=59, seconds=59)
        # If the ptf has no date set (for example because there are no positions)
        # we set the starting date for the research at the beginning of the calendar
        start_time = ptf.date if ptf.date else self._cal.start
        start_time = start_time.to_pydatetime()

        # Fetch trades from the database
        q = self._qb.select(self._TRADES_TABLE, rolling=('date',), keys=('ptf_uid',))
        qdata = (ptf.uid, start_time, end_time)
        trades = self._db.execute(q, qdata).fetchall()

        # If there are no trades just exit
        if not trades:
            return

        # Take cash position in portfolio base currency to increase/decrease with trades
        positions = ptf.constituents
        uid_list = ptf.constituents_uids

        # The cash position average loading price is expressed as the average fx
        # change rate paid to go from the position currency to the portfolio base
        # currency, hence for the base cash position alp = 1
        base_cash_pos = ptf.base_cash_obj
        if base_cash_pos is None:
            raise MissingData('No position in base currency {} for portfolio {}'
                              .format(ptf.currency, ptf.uid))
        cash_in_base_ccy = base_cash_pos.quantity
        assert base_cash_pos.alp == 1.

        # Cycle on trades grouping by position
        # ptf_uid, date, pos_uid, buy_sell, currency, quantity, price, costs, market
        for k, g in groupby(trades, key=lambda f: f[2]):

            # Sort by date
            gt = list(g)
            gt.sort(key=lambda f: f[1])

            # Get current values for the position
            try:
                v = positions[k]
            except KeyError:
                # If there is no position open for the asset we create a new one
                t_0 = gt[0]
                date_0 = pd.to_datetime(t_0[1])
                asset = self._af.get(t_0[2])
                # asset.load()
                v = self.new_position(t_0[2], date_0, asset.type, asset.currency,
                                      .0, 0, ptf.currency)
                uid_list.append(t_0[2])

            quantity = v.quantity
            alp = v.alp
            # pos_ccy = v.currency

            # Cycle through trades adjusting the values of quantities
            for t in gt:
                old_quantity = quantity
                old_alp = alp

                # We convert the trade price into the portfolio base currency
                # and we update the alp of the position accordingly.
                fx_rate = 1.
                if t[4] != ptf.currency:
                    pos_date = pd.to_datetime(t[1])
                    fx_obj = self._fx.get(t[4], ptf.currency)
                    fx_rate = fx_obj.get(pos_date)

                if t[3] == 1:
                    # BUY trade
                    quantity = old_quantity + t[5]
                    paid = t[6] * t[5] * fx_rate
                    alp = (old_alp * old_quantity + paid) / quantity
                    cash_in_base_ccy -= paid
                elif t[3] == 2:
                    # SELL trade
                    quantity = old_quantity - t[5]
                    received = t[6] * t[5] * fx_rate
                    cash_in_base_ccy += received
                else:
                    raise ValueError('Buy/Sell flag {} not recognized'.format(t[3]))

            if quantity <= 0.:
                del positions[k]
            else:
                # Update position
                v.quantity = quantity
                v.alp = alp
                positions[k] = v

        # Update base currency cash position
        base_cash_pos.quantity = cash_in_base_ccy
        ptf.base_cash_obj = base_cash_pos

        # Update portfolio
        ptf.constituents = positions
        ptf.date = self._cal.t0
        ptf.constituents_uids = uid_list
        del ptf.total_value
        del ptf.cnsts_df

    @staticmethod
    def total_value(ptf: Portfolio, date: pd.Timestamp) -> float:
        """ Get the total value of the portfolio calculated at the goven date. """
        tot_value = ptf.base_cash_pos.quantity
        for p in ptf.constituents.values():
            idx = p.obj.prices.loc[:date].last_valid_index()
            tot_value += p.quantity * p.obj.prices.at[idx]
        return tot_value

    def summary(self, ptf: Portfolio) -> tuple:
        """ Show the portfolio summary in the portfolio base currency. """
        date = self._cal.t0

        # Run trough positions and collect data for the summary
        data = []
        tot_cost, tot_value = .0, .0
        for p in ptf.constituents.values():
            if p.type == 'Cash':
                price = 1.
                if self._fx.base_ccy != ptf.currency:
                    price = p.obj.last_price(date)
            else:
                price = p.obj.last_price(date)  # * fx_rate
            cost = p.quantity * p.alp  # * fx_rate
            value = p.quantity * price
            ret = value / cost - 1.
            tot_cost += cost
            tot_value += value
            data.append((p.uid, p.type, p.quantity, p.alp, price, cost, value, ret))

        # Sort accordingly to the key <type, uid>
        data.sort(key=lambda t: (t[1], t[0]))

        # Add base cash position
        base_cash = ptf.base_cash_pos.quantity
        data.append(('Base cash', 'Cash', base_cash, None, None, None, base_cash, None))

        # Calculate total portfolio values and add at the end
        tot_ret = tot_value / tot_cost - 1.
        tot_value += base_cash
        data.append(('Total', None, None, None, None, tot_cost, tot_value, tot_ret))

        fields = ('uid', 'type', 'quantity', 'alp', 'price', 'cost', 'value', 'return')
        return fields, data
