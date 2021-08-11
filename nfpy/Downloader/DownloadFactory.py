#
# Downloads Factory Class
# Builds download pages, initialize and launch them to
# perform single downloads.
#

from requests import RequestException
from typing import KeysView

import nfpy.Calendar as Cal
import nfpy.DB as DB
from nfpy.Tools import (Singleton, Exceptions as Ex, Utilities as Ut)

from .BaseDownloader import BasePage
from .BaseProvider import BaseProvider
from .ECB import ECBProvider
from .IB import IBProvider
from .Investing import InvestingProvider
from .Yahoo import YahooProvider


class DownloadFactory(metaclass=Singleton):
    """ Factory to download data from internet. The basic element is the page
        that depends on both provider and ticker downloaded.
    """

    _DWN_TABLE = 'Downloads'
    _IMP_TABLE = 'Imports'
    _PROVIDERS = {
        "ECB": ECBProvider(),
        "IB": IBProvider(),
        "Investing": InvestingProvider(),
        "Yahoo": YahooProvider(),
    }

    def __init__(self):
        self._db = DB.get_db_glob()
        self._qb = DB.get_qb_glob()
        self._splits = []

    @property
    def download_table(self) -> str:
        return self._DWN_TABLE

    @property
    def providers(self) -> KeysView[str]:
        return self._PROVIDERS.keys()

    @property
    def splits(self) -> list:
        return self._splits

    @splits.setter
    def splits(self, v: tuple):
        self._splits.append(v)

    @staticmethod
    def print_parameters(page_obj: BasePage) -> int:
        """ Print out the parameters available to a page object. """
        if not page_obj.params:
            buf = 'No parameters required for this downloading page\n'
        else:
            buf = 'Available parameters\n req | name\n'
            for p in sorted(page_obj.params.keys()):
                prfx = '*' if p in page_obj._MANDATORY else ' '
                buf += f'  {prfx}  | {p}\n'
        print(buf)
        return len(page_obj.params)

    def provider_exists(self, provider: str) -> bool:
        """ Check if the provider is supported. """
        return provider in self._PROVIDERS

    def page_exists(self, provider: str, page: str) -> bool:
        """ Check if the page is supported for the given provider. """
        return page in self._PROVIDERS[provider].pages

    def get_provider(self, v: str) -> BaseProvider:
        return self._PROVIDERS[v]

    def fetch_downloads(self, provider: str = None, page: str = None,
                        ticker: str = None, active: bool = True) -> tuple:
        """ Fetch and filter download entries.

            Input:
                provider [str]: filter by provider
                page [str]: filter by page
                ticker [str]: filter by ticker
                active [bool]: consider only automatic downloads

            Output:
                data [list]: list of tuples, each one a fetched row
                fields [list]: list of database column names
        """
        return self._filter(
            self._DWN_TABLE,
            active,
            **{'provider': provider, 'page': page, 'ticker': ticker}
        )

    def fetch_imports(self, uid: str = None, provider: str = None,
                      item: str = None, active: bool = True) -> tuple:
        """ Filter imports entries.

            Input:
                uid [str]: uid to import for (default None)
                provider [str]: filter by provider (default None)
                item [str]: filter by import item (default None)
                active [bool]: consider only active imports (default True)

            Output:
                data [list]: list of tuples, each one a fetched row
                fields [list]: list of database column names
        """
        return self._filter(
            self._IMP_TABLE,
            active,
            **{'uid': uid, 'provider': provider, 'item': item}
        )

    def _filter(self, table: str, active: bool, **kwargs) -> tuple:
        keys = tuple(k for k, v in kwargs.items() if v is not None)
        fields = self._qb.get_fields(table)

        res = self._db.execute(
            self._qb.select(
                table,
                fields=fields,
                keys=keys,
                where='active = 1' if active else ''
            ),
            tuple(kwargs[k] for k in keys)
        ).fetchall()
        if not res:
            return [], fields

        return res, fields

    def create_page_obj(self, provider: str, page: str, ticker: str) -> BasePage:
        """ Return an un-initialized page object of the correct type.

            Input:
                provider [str]: provider to download from
                page [str]: data type searched
                ticker [str]: ticker to download

            Output:
                obj [BasePage]: page object to download with
        """
        try:
            prov = self._PROVIDERS[provider]
        except KeyError:
            raise ValueError(f"Provider {provider} not recognized")
        return prov.create_page_obj(page, ticker)

    def do_import(self, data: dict, incremental: bool) -> None:
        """ Take the importing object and runs the import. """
        prov = data['provider']
        imp_item = self._PROVIDERS[prov].get_import_item(data, incremental)
        imp_item.run()

    def run_download(self, do_save: bool = True, override_date: bool = False,
                     provider: str = None, page: str = None,
                     ticker: str = None, override_active: bool = False) -> None:
        """ Performs a bulk update of the system based on the 'auto' flag in the
            Downloads table. The entries are updated only in case the last
            last update has been done at least 'frequency' days ago.

            Input:
                do_save [bool]: save in database (default True)
                override_date [bool]: disregard last update date (default False)
                uid [uid]: download for a uid (default None)
                provider [str]: download for a provider (default None)
                page [str]: download for a page (default None)
                ticker [str]: download for a ticker (default None)
                override_active [bool]: disregard 'active' (default False)
        """
        active = not override_active
        upd_list, _ = self.fetch_downloads(provider=provider, page=page,
                                           ticker=ticker, active=active)
        print(f'We are about to download {len(upd_list)} items')

        # General variables
        today_dt = Cal.today(mode='date')
        q_upd = self._qb.update(self._DWN_TABLE, fields=('last_update',))

        for item in upd_list:
            provider, page_name, ticker, currency, _, upd_freq, last_upd = item

            # Check the last update to avoid too frequent updates
            if last_upd and not override_date:
                delta_days = (today_dt - last_upd).days
                if delta_days < int(upd_freq):
                    msg = f'[{provider}: {page_name}] -> ' \
                          f'{ticker} updated {delta_days} days ago'
                    print(msg)
                    continue

            # If the last update check is passed go on with the update
            try:
                print(f'{ticker} -> {provider}[{page_name}]')
                page = self.create_page_obj(provider, page_name, ticker)
                page.initialize(currency=currency)

                # Perform download and save results
                try:
                    page.fetch()
                except RuntimeWarning as w:
                    # DownloadFactory throws this error for codes != 200
                    Ut.print_wrn(w)
                    continue
                if do_save is True:
                    page.save()
                else:
                    page.printout()

            except (Ex.MissingData, Ex.IsNoneError, RuntimeError,
                    RequestException, ValueError) as e:
                print(e)
            else:
                if do_save is True:
                    data_upd = (today_dt, provider, page_name, ticker)
                    self._db.execute(q_upd, data_upd, commit=True)

    def run_import(self, uid: str = None, provider: str = None,
                   item: str = None, override_active: bool = False,
                   incremental: bool = False) -> None:
        """ Performs a bulk import of the system based on the 'auto' flag in the
            Imports table.

            Input:
                uid [str]: import for an uid (default None)
                provider [str]: import for a provider (default None)
                item [str]: import for the item (default None)
                override_active [bool]: disregard 'active' (default False)
                incremental [bool]: do an incremental import (default False)
        """
        active = not override_active
        import_list, fields = self.fetch_imports(provider=provider, item=item,
                                                 uid=uid, active=active)
        print(f'We are about to import {len(import_list)} items')

        for element in import_list:
            import_data = dict(zip(fields, element))
            # print(import_data)
            try:
                self.do_import(import_data, incremental)
            except Ex.CalendarError as cal:
                raise cal
            except (Ex.MissingData, Ex.IsNoneError,
                    RuntimeError, RequestException) as e:
                print(e)

        # TODO: introduce post-import adjustments for special dividends
        # print('Performing post-import adjustments')


def get_dwnf_glob() -> DownloadFactory:
    """ Returns the pointer to the global Downloads Factory. """
    return DownloadFactory()
