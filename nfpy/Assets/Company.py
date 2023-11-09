#
# Company class
# Base class for company database
#

import pandas as pd
from typing import Optional
import warnings

from nfpy.Calendar import get_calendar_glob

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
    def financials(self) -> pd.DataFrame:
        """ Return the dataframe of financials. """
        if not self._cnsts_loaded:
            self._load_cnsts()
        return self._cnsts_df

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
        """ Fetch the fundamentals from the database. """
        # Get the fundamental data form the database
        cal = get_calendar_glob()
        res = self._db.execute(
            self._qb.select(
                self._CONSTITUENTS_TABLE,
                fields=('code', 'freq', 'date', 'value'),
                keys=('uid',),
                rolling=['date']
            ),
            (
                self._uid,
                cal.yearly_calendar[0].to_pydatetime(),
                cal.yearly_calendar[-1].to_pydatetime()
            )
        ).fetchall()
        if not res:
            warnings.warn(f'No fundamental data found for {self._uid}')
            return

        # FIXME: this is probably the step that takes forever to run,
        #     one option could be to substitute it with a DB call.
        #     In principle everything could be pivoted
        idx = pd.MultiIndex.from_tuples(
            sorted(set((v[1], pd.to_datetime(v[2])) for v in res)),
            names=('date', 'freq')
        )
        uids = sorted(set(v[0] for v in res))
        df = pd.DataFrame(index=idx, columns=uids)

        # multiindex = set()
        # uids = set()
        # for v in res:
        #     dt = pd.to_datetime(v[2])
        #     multiindex.add((v[1], dt))
        #     uids.add(v[0])
        #
        # idx = pd.MultiIndex.from_tuples(
        #     sorted(multiindex),
        #     names=('date', 'freq')
        # )
        # df = pd.DataFrame(index=idx, columns=sorted(uids))

        for v in res:
            dt = pd.to_datetime(v[2])
            df.at[(v[1], dt), v[0]] = v[3]

        self._cnsts_df = df
        self._cnsts_uids = uids

        # Signal constituents loaded
        self._cnsts_loaded = True
