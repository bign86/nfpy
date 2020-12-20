#
# Import Factory Class
# Imports data to the elaboration database
#

from requests import RequestException

import nfpy.DB as DB
from nfpy.Tools import (Singleton, Exceptions as Ex)

from .ECB import ECBProvider
from .IB import IBProvider
from .Investing import InvestingProvider
from .Yahoo import YahooProvider


class ImportFactory(metaclass=Singleton):

    _TABLE = 'Imports'
    _PROVIDERS = {  # "Morningstar": MorningstarProvider(),
                  "Yahoo": YahooProvider(),
                  "ECB": ECBProvider(),
                  "Investing": InvestingProvider(),
                  "IB": IBProvider()
                  }

    def __init__(self):
        self._db = DB.get_db_glob()
        self._qb = DB.get_qb_glob()
        self._imports_list = None

    def imports_by_uid(self, uid: str = None, provider: str = None, page: str = None,
                       ticker: str = None, active: bool = True) -> tuple:
        """ Return all import entries by uid.

            Input:
                uid [str]: uid to import for (default None)
                provider [str]: filter by provider (default None)
                page [str]: filter by page (default None)
                ticker [str]: filter by ticker (default None)
                active [bool]: consider only active imports (default True)

            Output:
                fields [list]: list of database column names
                data [list]: list of tuples, each one a fetched row
        """
        fields = list(self._qb.get_fields(self._TABLE))
        w_cond = 'active = 1' if active else ''
        k_cond, params = [], ()
        if uid:
            k_cond.append('uid')
            params += (uid, )
        if provider:
            k_cond.append('provider')
            params += (provider, )
        if page:
            k_cond.append('page')
            params += (page, )
        if ticker:
            k_cond.append('ticker')
            params += (ticker, )

        q_uid = self._qb.select(self._TABLE, fields=fields, keys=k_cond, where=w_cond)
        res = self._db.execute(q_uid, params).fetchall()
        if not res:
            return fields, None

        self._imports_list = res
        return fields, res, len(res)

    def do_import(self, data: dict):
        """ Pass the call input to the underlying page. """
        if data['provider'] not in self._PROVIDERS:
            raise ValueError("Provider {} not recognized".format(data['provider']))
        self._PROVIDERS[data['provider']].do_import(data)

    def bulk_import(self, uid: str = None, provider: str = None, page: str = None,
                    ticker: str = None, override_active: bool = False):
        """ Performs a bulk import of the system based on the 'auto' flag in the
            Imports table.

            Input:
                uid [str]: import for an uid (default None)
                provider [str]: import for a provider (default None)
                page [str]: import for a page (default None)
                ticker [str]: import for a ticker (default None)
                override_active [bool]: disregard 'active' (default False)
        """
        active = not override_active
        fields, import_list, num = self.imports_by_uid(provider=provider, page=page,
                                                       uid=uid, ticker=ticker,
                                                       active=active)
        print('We are about to import {} items'.format(num))

        for item in import_list:
            import_data = dict(zip(fields, item))
            try:
                print(import_data)
                self.do_import(import_data)
            except Ex.CalendarError as cal:
                raise cal
            except (Ex.MissingData, Ex.IsNoneError,
                    RuntimeError, RequestException) as e:
                print(e)


def get_impf_glob() -> ImportFactory:
    """ Returns the pointer to the global Imports Factory. """
    return ImportFactory()
