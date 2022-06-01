#
# Downloads Factory Class
# Builds download pages, initialize and launch them to
# perform single downloads.
#

from collections import namedtuple, defaultdict
from requests import RequestException
from typing import (KeysView, Optional)

from nfpy.Assets import get_af_glob
import nfpy.Calendar as Cal
import nfpy.DB as DB
from nfpy.Tools import (Singleton, Exceptions as Ex, Utilities as Ut)

from .BaseDownloader import BasePage

# Namedtuples holding the data for downloads and imports
NTDownload = namedtuple(
    'NTDownload',
    'provider, page, ticker, currency, active, update_frequency, last_update'
)

NTImport = namedtuple('NTImport', 'uid, ticker, provider, item, active')


class DownloadFactory(metaclass=Singleton):
    """ Factory to download data from internet. The basic element is the page
        that depends on both provider and ticker downloaded.
    """

    _DWN_TABLE = 'Downloads'
    _IMP_TABLE = 'Imports'
    _PROV_TABLE = 'Providers'

    def __init__(self):
        self._af = get_af_glob()
        self._db = DB.get_db_glob()
        self._qb = DB.get_qb_glob()
        self._splits = []

        objs = self._db.execute(
            f'select provider, page, item from {self._PROV_TABLE}'
        ).fetchall()
        self._dwn_obj = defaultdict(list)
        for k, v in set((v[0], v[1]) for v in objs):
            self._dwn_obj[k].append(v)
        self._imp_obj = defaultdict(list)
        for k, v in set((v[0], v[2]) for v in objs):
            self._imp_obj[k].append(v)

    @property
    def download_table(self) -> str:
        return self._DWN_TABLE

    @property
    def providers(self) -> KeysView[str]:
        return self._dwn_obj.keys()

    @property
    def splits(self) -> list:
        return self._splits

    @splits.setter
    def splits(self, v: tuple) -> None:
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
        return provider in self._dwn_obj

    def page_exists(self, provider: str, page: str) -> bool:
        """ Check if the page is supported for the given provider. """
        return page in self._dwn_obj[provider]

    def fetch_downloads(self, provider: Optional[str] = None,
                        page: Optional[str] = None,
                        ticker: Optional[str] = None, active: bool = True) \
            -> tuple[NTDownload]:
        """ Fetch and filter download entries.

            Input:
                provider [Optional[str]]: filter by provider (default: None)
                page [Optional[str]]: filter by page (default: None)
                ticker [Optional[str]]: filter by ticker (default: None)
                active [bool]: consider only automatic downloads (default: True)

            Output:
                data [list]: list of tuples, each one a fetched row
                fields [list]: list of database column names
        """
        return self._filter(
            self._DWN_TABLE,
            NTDownload,
            active,
            {'provider': provider, 'page': page, 'ticker': ticker}
        )

    def fetch_imports(self, uid: Optional[str] = None,
                      provider: Optional[str] = None,
                      item: Optional[str] = None, active: bool = True) \
            -> tuple[NTImport]:
        """ Filter imports entries.

            Input:
                uid [Optional[str]]: uid to import for (default: None)
                provider [Optional[str]]: filter by provider (default: None)
                item [Optional[str]]: filter by import item (default: None)
                active [bool]: consider only active imports (default: True)

            Output:
                data [list]: list of tuples, each one a fetched row
                fields [list]: list of database column names
        """
        return self._filter(
            self._IMP_TABLE,
            NTImport,
            active,
            {'uid': uid, 'provider': provider, 'item': item}
        )

    def _filter(self, table: str, tuple_obj: namedtuple, active: bool,
                options: dict) -> tuple:
        """ Filters the Downloads or Imports table to return the items selected
            using the available filters.
        """
        keys = tuple(k for k, v in options.items() if v is not None)

        return tuple(
            map(
                tuple_obj._make,
                self._db.execute(
                    self._qb.select(
                        table,
                        fields=tuple_obj._fields,
                        keys=keys,
                        where='active = 1' if active else ''
                    ),
                    tuple(options[k] for k in keys)
                ).fetchall()
            )
        )

    def create_page_obj(self, provider: str, page: str, ticker: str) -> BasePage:
        """ Return an un-initialized page object of the correct type.

            Input:
                provider [str]: provider to download from
                page [str]: data type searched
                ticker [str]: ticker to download

            Output:
                obj [BasePage]: page object to download with
        """
        if page not in self._dwn_obj[provider]:
            raise ValueError(f"Page {page} not available for {provider}")

        symbol = '.' + '.'.join([provider, page + 'Page'])
        class_ = Ut.import_symbol(symbol, pkg='nfpy.Downloader')
        return class_(ticker)

    def do_import(self, data: NTImport, incremental: bool) -> None:
        """ Take the importing object and runs the import. """
        if data.item not in self._imp_obj[data.provider]:
            raise ValueError(f"Item {data.item} not available for {data.provider}")

        symbol = '.' + '.'.join([data.provider, data.item + 'Item'])
        class_ = Ut.import_symbol(symbol, pkg='nfpy.Downloader')

        asset = self._af.get(data.uid)
        data = data._asdict()
        if asset.type == 'Company':
            data['dst_table'] = asset.constituents_table
        else:
            data['dst_table'] = asset.ts_table

        imp_item = class_(data, incremental)
        imp_item.run()

    def run_download(self, do_save: bool = True, override_date: bool = False,
                     provider: Optional[str] = None, page: Optional[str] = None,
                     ticker: Optional[str] = None,
                     override_active: bool = False) -> None:
        """ Performs a bulk update of the system based on the 'auto' flag in the
            Downloads table. The entries are updated only in case the last
            last update has been done at least 'frequency' days ago.

            Input:
                do_save [bool]: save in database (default: True)
                override_date [bool]: disregard last update date (default: False)
                provider [Optional[str]]: download for a provider (default: None)
                page [Optional[str]]: download for a page (default: None)
                ticker [Optional[str]]: download for a ticker (default: None)
                override_active [bool]: disregard 'active' (default: False)
        """
        active = not override_active
        upd_list = self.fetch_downloads(
            provider=provider, page=page, ticker=ticker, active=active
        )
        print(f'We are about to download {len(upd_list)} items')

        # General variables
        today_dt = Cal.today(mode='date')
        q_upd = self._qb.update(self._DWN_TABLE, fields=('last_update',))

        # loop = asyncio.get_running_loop()

        count_done = 0
        count_skipped = 0
        count_failed = 0
        for item in upd_list:
            # Check the last update to avoid too frequent updates
            if item.last_update and not override_date:
                delta_days = (today_dt - item.last_update).days
                if delta_days < int(item.update_frequency):
                    msg = f'[{item.provider}: {item.page}] -> ' \
                          f'{item.ticker} updated {delta_days} days ago'
                    print(msg)
                    count_skipped += 1
                    continue

            # If the last update check is passed go on with the update
            try:
                print(f'{item.ticker} -> {item.provider}[{item.page}]')
                # await loop.run_in_executor(None, self.do_test_download, item, do_save)
                try:
                    page = self.create_page_obj(
                        item.provider, item.page, item.ticker
                    ) \
                        .initialize(params={'currency': item.currency}) \
                        .fetch()
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
                count_failed += 1
            else:
                count_done += 1
                if do_save is True:
                    data_upd = (today_dt, item.provider, item.page, item.ticker)
                    self._db.execute(q_upd, data_upd, commit=True)

        print(
            f'\nItems downloaded: {count_done:>4}'
            f'\nItems skipped:    {count_skipped:>4}'
            f'\nItems failed:     {count_failed:>4}\n'
        )

    def run_import(self, uid: Optional[str] = None,
                   provider: Optional[str] = None,
                   item: Optional[str] = None, override_active: bool = False,
                   incremental: bool = False) -> None:
        """ Performs a bulk import of the system based on the 'auto' flag in the
            Imports table.

            Input:
                uid [Optional[str]]: import for an uid (default: None)
                provider [Optional[str]]: import for a provider (default: None)
                item [Optional[str]]: import for the item (default: None)
                override_active [bool]: disregard 'active' (default: False)
                incremental [bool]: do an incremental import (default: False)
        """
        active = not override_active
        import_list = self.fetch_imports(
            provider=provider, item=item, uid=uid, active=active
        )
        print(f'We are about to import {len(import_list)} items')

        for element in import_list:
            try:
                self.do_import(element, incremental)
            except Ex.CalendarError as cal:
                raise cal
            except (Ex.MissingData, Ex.IsNoneError,
                    RuntimeError, RequestException) as e:
                print(e)


def get_dwnf_glob() -> DownloadFactory:
    """ Returns the pointer to the global Downloads Factory. """
    return DownloadFactory()
