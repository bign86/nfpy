#
# ETF class
# Base class for ETFs
#

from .Equity import Equity


class Etf(Equity):
    """ Base class for ETFs """

    _TYPE = 'Etf'
    _BASE_TABLE = 'Etf'
    _TS_TABLE = 'EtfTS'

    def __init__(self, uid: str):
        super().__init__(uid)
        self._fee = None

    # FIXME: fees are not currently used
    @property
    def fees(self) -> float:
        """ Annual fees. """
        return self._fee

    @fees.setter
    def fees(self, v: float):
        self._fee = v
