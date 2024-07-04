#
# Downloads Factory Class
# Builds download pages, initialize and launch them to
# perform single downloads.
#

from collections import defaultdict
from itertools import groupby
from requests import RequestException
from typing import (KeysView, Optional)

from nfpy.Assets import get_af_glob
import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO.Utilities as Ut
from nfpy.Tools import (
    get_logger_glob,
    Singleton,
    Exceptions as Ex,
    Utilities as Uti
)

from .BaseProvider import get_provider
from .Objs import *


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

        self.q_upd = self._qb.update(self._DWN_TABLE, fields=('last_update',))

        objs = self._db.execute(
            f'SELECT [provider], [page], [item] FROM [{self._PROV_TABLE}] WHERE [deprecated] IS False'
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

    def pages(self, provider: str) -> list:
        return self._dwn_obj[provider]

    @property
    def splits(self) -> list:
        return self._splits

    @splits.setter
    def splits(self, v: tuple) -> None:
        self._splits.append(v)

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
            using the available filters, ordering by <provider>.
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
                        where='active = 1' if active else '',
                        order='provider'
                    ),
                    tuple(options[k] for k in keys)
                ).fetchall()
            )
        )

    def do_import(self, data: NTImport, incremental: bool) -> None:
        """ Take the importing object and runs the import. """
        if data.item not in self._imp_obj[data.provider]:
            raise ValueError(f"Item {data.item} not available for {data.provider}")

        symbol = '.' + '.'.join([data.provider, data.item + 'Item'])
        class_ = Uti.import_symbol(symbol, pkg='nfpy.Downloader')

        asset = self._af.get(data.uid)
        data = data._asdict()
        data['currency'] = asset.currency
        if asset.type == 'Company':
            data['dst_table'] = asset.constituents_table
        else:
            data['dst_table'] = asset.ts_table

        imp_item = class_(data, incremental)
        imp_item.run()

    def run_download(
            self,
            do_save: bool = True,
            override_date: bool = False,
            provider: str | None = None,
            page: str | None = None,
            ticker: str | None = None,
            override_active: bool = False
    ) -> None:
        """ Performs a bulk update of the system based on the 'auto' flag in the
            Downloads table. The entries are updated only in case the last
            update has been done at least 'frequency' days ago.

            Input:
                do_save [bool]: save in database (default: True)
                override_date [bool]: disregard last update date (default: False)
                provider [str | None]: download for a provider (default: None)
                page [str | None]: download for a page (default: None)
                ticker [str | None]: download for a ticker (default: None)
                override_active [bool]: disregard 'active' (default: False)
        """
        today = Cal.today(mode='date')
        active = not override_active
        upd_list = self.fetch_downloads(
            provider=provider, page=page, ticker=ticker, active=active
        )
        print(f'We are about to download {len(upd_list)} items')
        logger = get_logger_glob()
        logger.log(20, f'{len(upd_list)} items have been fetched from DB')

        count_done = 0
        count_skipped = 0
        count_failed = 0
        for provider, group in groupby(upd_list, key=lambda v: v.provider):
            logger.log(20, f'Provider {provider}')

            # Get the correct provider and the download generator from it
            skipped, generator = get_provider(provider)() \
                .get_download_generator(group, override_date)
            count_skipped += skipped
            for d, page in generator:
                try:
                    print(f'{d.ticker} -> {d.provider}[{d.page}]')
                    page.initialize(params={}) \
                        .fetch()
                    _ = page.data

                except (Ex.MissingData, Ex.IsNoneError, RuntimeError,
                        RequestException, ValueError, ConnectionError) as e:
                    Ut.print_exc(e)
                    count_failed += 1
                except RuntimeWarning as w:
                    Ut.print_wrn(w)
                    data_upd = (today, d.provider, d.page, d.ticker)
                    self._db.execute(self.q_upd, data_upd, commit=True)
                    count_done += 1
                else:
                    if do_save is True:
                        page.save()
                        data_upd = (today, d.provider, d.page, d.ticker)
                        self._db.execute(self.q_upd, data_upd, commit=True)
                    else:
                        page.printout()
                    count_done += 1

        msg = f'Items downloaded: {count_done:>4}\n' \
            f'Items skipped:    {count_skipped:>4}\n' \
            f'Items failed:     {count_failed:>4}\n'
        print(msg)
        logger.log(20, msg)

        self._db.execute(
            'UPDATE [SystemInfo] SET [date] = ? WHERE [field] = "lastDownload";',
            (today,), commit=True
        )
        logger.log(20, 'Download completed')

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
        logger = get_logger_glob()
        logger.log(20, f'We are about to import {len(import_list)} items')

        for element in import_list:
            try:
                self.do_import(element, incremental)
            except Ex.CalendarError as cal:
                raise cal
            except (Ex.MissingData, Ex.IsNoneError,
                    RuntimeError, ValueError, RequestException) as e:
                Ut.print_exc(e)

        self._db.execute(
            'UPDATE [SystemInfo] SET [date] = ? WHERE [field] = "lastImport";',
            (Cal.today(mode='date'),), commit=True
        )
        logger.log(20, 'Import completed')


def get_dwnf_glob() -> DownloadFactory:
    """ Returns the pointer to the global Downloads Factory. """
    return DownloadFactory()
