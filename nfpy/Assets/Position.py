#
# Auxiliary portfolio classes
# Base class for a portfolio
#

import pandas as pd

from nfpy.Tools import Utilities as Ut


class Position(Ut.AttributizedDict):
    """ Position class, contains the information on a single portfolio position. """

    def __init__(self, pos_uid: str, date: pd.Timestamp, atype: str,
                 currency: str, alp: float, quantity: float):
        super().__init__(self)
        self.uid = pos_uid
        self.date = date
        self.currency = currency  # position currency
        self.alp = alp
        self.quantity = quantity
        self.type = atype  # type of asset


class Trade(Ut.AttributizedDict):

    def __init__(self):
        super().__init__(self)
        self.ptf_uid = ''
        self.date = pd.Timestamp()
        self.pos_uid = ''
        self.buy_sell = -1
        self.currency = ''
        self.quantity = .0
        self.price = .0
        self.costs = .0
        self.market = ''

# def new_trade(self, ptf_uid: str, date: Union[str, datetime, pd.Timestamp],
#               pos_uid: str, buy_sell: int, currency: str, quantity: float, price: float,
#               costs: float = None, market: str = None, date_fmt: str = '%Y-%m-%d %H:%M:%S'):
#     date = date_2_datetime(date, fmt=date_fmt)
#     q = self._qb.insert(self._TRADES_TABLE)
#     data = (ptf_uid, date, pos_uid, buy_sell, currency, quantity, price, costs, market)
#     self._db.execute(q, data, commit=True)
#
#
# def delete_trade(self, ptf_uid: str, date: pd.Timestamp, pos_uid: str):
#     q = self._qb.delete(self._TRADES_TABLE)
#     data = (ptf_uid, date, pos_uid)
#     self._db.execute(q, data, commit=True)
#
#
# def new_position(self, pos_uid: str, date: pd.Timestamp, atype: str,
#                  currency: str, alp: float, quantity: float, base_ccy: str) -> Position:
#     if atype == 'Cash':
#         a_obj = self._fx.get(currency, base_ccy)
#     else:
#         a_obj = self._af.get(pos_uid)
#     return Position(pos_uid, date, atype, currency, alp, quantity, a_obj)
