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
    _PROVIDERS = {
        "Yahoo": YahooProvider(),
        "ECB": ECBProvider(),
        "Investing": InvestingProvider(),
        "IB": IBProvider()
    }

    def __init__(self):
        self._db = DB.get_db_glob()
        self._qb = DB.get_qb_glob()
        self._imports_list = None

    def filter_imports(self, uid: str = None, provider: str = None,
                       item: str = None, active: bool = True) -> tuple:
        """ Filter imports entries.

            Input:
                uid [str]: uid to import for (default None)
                provider [str]: filter by provider (default None)
                item [str]: filter by import item (default None)
                active [bool]: consider only active imports (default True)

            Output:
                fields [list]: list of database column names
                data [list]: list of tuples, each one a fetched row
        """
        fields = list(self._qb.get_fields(self._TABLE))
        w = 'active = 1' if active else ''
        k, params = [], ()
        if uid:
            k.append('uid')
            params += (uid,)
        if provider:
            k.append('provider')
            params += (provider,)
        if item:
            k.append('item')
            params += (item,)

        q_uid = self._qb.select(self._TABLE, fields=fields, keys=k, where=w)
        res = self._db.execute(q_uid, params).fetchall()
        if not res:
            return fields, None

        self._imports_list = res
        return fields, res, len(res)

    def do_import(self, data: dict) -> None:
        """ Take the importing object and runs the import. """
        prov = data['provider']
        imp_item = self._PROVIDERS[prov].get_import_item(data)
        imp_item.run()

    def bulk_import(self, uid: str = None, provider: str = None,
                    item: str = None, override_active: bool = False):
        """ Performs a bulk import of the system based on the 'auto' flag in the
            Imports table.

            Input:
                uid [str]: import for an uid (default None)
                provider [str]: import for a provider (default None)
                item [str]: import for the item (default None)
                override_active [bool]: disregard 'active' (default False)
        """
        active = not override_active
        fields, import_list, num = self.filter_imports(provider=provider,
                                                       item=item,
                                                       uid=uid,
                                                       active=active)
        print('We are about to import {} items'.format(num))

        for element in import_list:
            import_data = dict(zip(fields, element))
            print(import_data)
            try:
                self.do_import(import_data)
            except Ex.CalendarError as cal:
                raise cal
            except (Ex.MissingData, Ex.IsNoneError,
                    RuntimeError, RequestException) as e:
                print(e)


def get_impf_glob() -> ImportFactory:
    """ Returns the pointer to the global Imports Factory. """
    return ImportFactory()
