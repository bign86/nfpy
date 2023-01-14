#
# Company class
# Base class for company database
#

import pandas as pd
from typing import Optional
import warnings

from .AggregationMixin import AggregationMixin
from .FinancialItem import FinancialItem


class Company(AggregationMixin, FinancialItem):
    """ Base class for companies. """

    _TYPE = 'Company'
    _BASE_TABLE = 'Company'
    _CONSTITUENTS_TABLE = 'CompanyFundamentals'

    def __init__(self, uid: str):
        super().__init__(uid)
        self._equity = None
        self._rating = None

    @property
    def equity(self) -> str:
        return self._equity

    @equity.setter
    def equity(self, v: str):
        self._equity = v

    @property
    def rating(self) -> Optional[str]:
        return self._rating

    @rating.setter
    def rating(self, v: str) -> None:
        self._rating = v

    def _load_cnsts(self) -> None:
        """ Fetch from the database the fundamentals. """
        # Get the fundamental data form the database
        res = self._db.execute(
            self._qb.select(
                self._CONSTITUENTS_TABLE,
                fields=('code', 'freq', 'date', 'value'),
                keys=('uid',)
            ),
            (self._uid,)
        ).fetchall()
        if not res:
            warnings.warn(f'No fundamental data found for {self._uid}')
            return

        idx = pd.MultiIndex.from_tuples(
            sorted(set((v[1], pd.to_datetime(v[2])) for v in res)),
            names=('date', 'freq')
        )
        uids = sorted(set(v[0] for v in res))
        df = pd.DataFrame(index=idx, columns=uids)

        for v in res:
            dt = pd.to_datetime(v[2])
            df.at[(v[1], dt), v[0]] = v[3]

        self._cnsts_df = df
        self._cnsts_uids = uids

        # Signal constituents loaded
        self._cnsts_loaded = True
