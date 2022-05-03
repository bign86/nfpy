#
# Fx class
# Class for exchange rates
#

from .Asset import Asset


class Fx(Asset):
    """ Class for exchange rates. """

    _TYPE = 'Fx'
    _BASE_TABLE = 'Fx'
    _TS_TABLE = 'FxTS'
    _TS_ROLL_KEY_LIST = ['date']
