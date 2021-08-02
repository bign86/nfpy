#
# Company class
# Base class for company database
#

from itertools import groupby
import pandas as pd
import warnings

from .AggregationMixin import AggregationMixin
from .FinancialItem import FinancialItem


class Company(AggregationMixin, FinancialItem):
    """ Base class for companies. """

    _TYPE = 'Company'
    _BASE_TABLE = 'Company'
    _CONSTITUENTS_TABLE = 'CompanyFundamentals'

    def _load_cnsts(self):
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

        # Create the sorted indices per date
        id_a = sorted(set(pd.to_datetime(v[2]) for v in res if v[1] == 'A'))
        id_q = sorted(set(pd.to_datetime(v[2]) for v in res if v[1] == 'Q'))

        # Build the constituents data series
        avail_data = []
        # for code, g in groupby(_r, key=lambda f: f[0]):
        for k, g in groupby(res, key=lambda f: f[0]):
            has_a, has_q = False, False
            s_a = pd.Series(index=id_a)
            s_q = pd.Series(index=id_q)
            for v in list(g):
                date = pd.to_datetime(v[2])

                # Populate the correct series
                if v[1] == 'A':
                    s_a.at[date] = v[3]
                    has_a = True
                else:
                    s_q.at[date] = v[3]
                    has_q = True

            # Populate the final dictionary
            if has_a:
                self._dict_cnsts[('A', k)] = s_a
                avail_data.append(('A', k))
            if has_q:
                self._dict_cnsts[('Q', k)] = s_q
                avail_data.append(('Q', k))
        self._cnsts_uids = avail_data

        # Signal constituents loaded
        self._cnsts_loaded = True
