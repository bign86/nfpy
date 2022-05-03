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
