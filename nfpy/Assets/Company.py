#
# Company class
# Base class for company database
#
import warnings

import pandas as pd
from itertools import groupby

from nfpy.Assets.FinancialItem import FinancialItem
from nfpy.Assets.AggregationMixin import AggregationMixin
# from nfpy.Handlers.CurrencyFactory import get_fx_glob
# from nfpy.Tools.Exceptions import MissingData


class Company(AggregationMixin, FinancialItem):
    """ Base class for companies. """

    _TYPE = 'Company'
    _BASE_TABLE = 'Company'
    _CONSTITUENTS_TABLE = 'CompanyFundamentals'

    def __init__(self, uid: str):
        super().__init__(uid)
        # self._fx = get_fx_glob()
        # self._equity = None
        # self._name = None
        # self._curr = None

    # @property
    # def equity(self) -> str:
    #     return self._equity
    #
    # @equity.setter
    # def equity(self, v: str):
    #     self._equity = v

    # @property
    # def name(self) -> str:
    #     return self._name
    #
    # @name.setter
    # def name(self, v: str):
    #     self._name = v

    # @property
    # def currency(self) -> str:
    #     return self._curr
    #
    # @currency.setter
    # def currency(self, v: str):
    #     self._curr = v

    def _load_cnsts(self):
        """ Fetch from the database the fundamentals. """
        # Define the list of fields to fetch
        fields = ['code', 'freq', 'date', 'value']

        # Get the fundamental data form the database
        q = self._qb.select(self._CONSTITUENTS_TABLE, fields=fields, keys=('uid',))
        res = self._db.execute(q, (self._uid,)).fetchall()
        if not res:
            warnings.warn('No fundamental data found for {}'.format(self._uid))
            return

        # Create the sorted indices per date
        id_a = sorted(set(pd.to_datetime(v[2]) for v in res if v[1] == 'A'))
        id_q = sorted(set(pd.to_datetime(v[2]) for v in res if v[1] == 'Q'))

        # Take the currency conversion
        # cv_obj = self._fx.get(self._curr)

        # Build the constituents data series
        avail_data = []
        # for code, g in groupby(_r, key=lambda f: f[0]):
        for k, g in groupby(res, key=lambda f: f[0]):
            has_a, has_q = False, False
            # k = self._dt.teg(code)
            s_a = pd.Series(index=id_a)
            s_q = pd.Series(index=id_q)
            for v in list(g):
                date = pd.to_datetime(v[2])

                # Populate the correct series
                if v[1] == 'A':
                    s_a.at[date] = v[3]  # * cv_obj.get(date)
                    has_a = True
                else:
                    s_q.at[date] = v[3]  # * cv_obj.get(date)
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
