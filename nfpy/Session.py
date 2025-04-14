#
# Class Session
# To use the calendar and store the loaded data
#

from typing import Optional

from nfpy.Calendar import Calendar, TyDate
from nfpy.Tools import (Singleton)


class Session(metaclass=Singleton):

    def __init__(self):
        self._cal = None
        self._assets = {}

    def __bool__(self) -> bool:
        return self._cal is not None

    @property
    def calendar(self) -> Calendar:
        return self._cal

    def initialize(
        self,
        end: TyDate,
        start: Optional[TyDate] = None,
        periods: Optional[int] = None,
        monthly_start: Optional[TyDate] = None,
        monthly_periods: Optional[int] = None,
        yearly_start: Optional[TyDate] = None,
        yearly_periods: Optional[int] = None,
        fmt: str = '%Y-%m-%d'
    ) -> None:
        """ Initialize the session with a calendar """
        self._cal = Calendar()
        self._cal.initialize(
            end=end,
            start=start,
            periods=periods,
            monthly_start=monthly_start,
            monthly_periods=monthly_periods,
            yearly_start=yearly_start,
            yearly_periods=yearly_periods,
            fmt=fmt
        )
        self._assets = {}

    def shutoff(self) -> None:
        """ Shut off the session """
        self._cal = None
        self._assets = {}

    @property
    def assets(self) -> dict:
        return self._assets


def get_session() -> Session:
    """ Returns the pointer to the global DB """
    return Session()
