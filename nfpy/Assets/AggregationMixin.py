#
# Mixin aggregation class
# Mixin class for aggregations, adds the support for constituents to a base class
#

import pandas as pd
from typing import TypeVar

from nfpy.Calendar import get_calendar_glob


class AggregationMixin(object):
    """ Mixin class for aggregations of assets. """

    _CONSTITUENTS_TABLE = ''

    def __init__(self, uid: str):
        super().__init__(uid)
        self._cnsts_loaded = False
        self._dict_cnsts = {}
        self._cnsts_uids = []

        cal = get_calendar_glob().calendar
        self._cnsts_df = pd.DataFrame(index=cal)

    def __contains__(self, uid: str) -> bool:
        return uid in self._cnsts_uids

    @property
    def constituents_table(self) -> str:
        return self._CONSTITUENTS_TABLE

    @property
    def constituents(self) -> dict:
        """ Return the dictionary of constituents. """
        return self._dict_cnsts

    @constituents.setter
    def constituents(self, cnst: dict):
        self._dict_cnsts = cnst

    @property
    def constituents_uids(self) -> list:
        """ Return the sorted list of constituents uids. The sorting must
            be defined by the child object.
        """
        return self._cnsts_uids

    @constituents_uids.setter
    def constituents_uids(self, uids: list):
        self._cnsts_uids = uids

    @property
    def num_constituents(self) -> int:
        return len(self._cnsts_uids)

    @property
    def cnsts_df(self) -> pd.DataFrame:
        return self._cnsts_df

    # FIXME: better to return None?
    @property
    def prices(self):
        raise NotImplementedError("Aggregations do not have price levels!")

    def load(self):
        """ Load the portfolio from base table and load the constituents.
            Overrides the one in Asset.
        """
        super().load()
        if not self._cnsts_loaded:
            self._load_cnsts()

    def write_cnsts(self):
        """ Save to the database the constituents of the aggregation. """
        self._write_cnsts()

    # FIXME: better to pass?
    def calc_returns(self):
        raise NotImplementedError('To be implemented in child classes')

    # FIXME: better to pass?
    def calc_log_returns(self):
        raise NotImplementedError('To be implemented in child classes')

    def _load_cnsts(self):
        """ Fetch from the database the constituents. """
        raise NotImplementedError('To be implemented in child classes.')

    def _write_cnsts(self):
        """ Save to the database the constituents. """
        raise NotImplementedError('To be implemented in child classes.')


TyAggregation = TypeVar('TyAggregation', bound=AggregationMixin)
