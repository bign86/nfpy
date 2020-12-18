#
# Currency class
# Class for currencies saved as change ratio against another currency
#

from .Asset import Asset


class Currency(Asset):
    """ Class for currencies """

    _TYPE = 'Currency'
    _BASE_TABLE = 'Currency'
    _TS_TABLE = 'CurrencyTS'
    _TS_ROLL_KEY_LIST = ['date']
