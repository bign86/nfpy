#
# Downloads Factory Class
# Builds download pages, initialize and launch them to
# perform single downloads.
#

import datetime
from pathlib import Path
from typing import List, Union
from requests import RequestException

from nfpy.DB.DB import get_db_glob
from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Downloader.BaseDownloader import BasePage
from nfpy.Handlers.Calendar import today_
from nfpy.Tools.Exceptions import MissingData, IsNoneError
from nfpy.Tools.Singleton import Singleton

# from .Morningstar import MorningstarProvider
from .ECB import ECBProvider
from .Yahoo import YahooProvider
from .Investing import InvestingProvider
from .IB import IBProvider


class DownloadFactory(metaclass=Singleton):
    """ Factory to download data from internet. The basic element is the page that
        depends on both provider and ticker downloaded.
    """

    _TABLE = 'Downloads'
    _PROVIDERS = {  # "Morningstar": MorningstarProvider(),
                  "Yahoo": YahooProvider(),
                  "ECB": ECBProvider(),
                  "Investing": InvestingProvider(),
                  "IB": IBProvider()
                  }

    def __init__(self):
        self._db = get_db_glob()
        self._qb = get_qb_glob()
        self._downloads_list = None

    def providers(self) -> List:
        """ Return a list of _all_ available providers. """
        return list(self._PROVIDERS.keys())

    def pages(self, provider: str) -> List:
        """ Return a list of _all_ available pages for the given provider. """
        return list(self._PROVIDERS[provider].pages)

    @staticmethod
    def print_parameters(page_obj: BasePage) -> int:
        """ Print out the parameters available to a page object. """
        if not page_obj.params:
            buf = 'No parameters required for this downloading page\n'
        else:
            buf = 'Available parameters\n req | name\n'
            for p in sorted(page_obj.params.keys()):
                prfx = '  *  | ' if p in page_obj._MANDATORY else '     | '
                buf += prfx + p + '\n'
        print(buf)
        return len(page_obj.params)

    def provider_exists(self, provider: str) -> bool:
        """ Check if a provider is supported. """
        return provider in self._PROVIDERS

    def page_exists(self, provider: str, page: str) -> bool:
        """ Check if a page for the given provider is supported. """
        return page in self._PROVIDERS[provider].pages

    def downloads_by_uid(self, provider: str = None, page: str = None,
                         uid: str = None, ticker: str = None, active: bool = True) -> tuple:
        """ Return all download entries by uid.

            Input:
                provider [str]: filter by provider
                page [str]: filter by page
                uid [str]: uid to download. If none all uids are considered
                ticker [str]: filter by ticker
                active [bool]: consider only automatic downloads

            Output:
                fields [list]: list of database column names
                data [list]: list of tuples, each one a fetched row
        """
        fields = ['uid', 'provider', 'page', 'ticker', 'currency',
                  'update_frequency', 'last_update']
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
            return fields, None, 0

        self._downloads_list = res
        return fields, res, len(res)

    def _calc_default_input(self, prov: str, ticker: str, table: str) -> dict:
        return self._PROVIDERS[prov].calc_default_input(ticker, table)

    def create_page_obj(self, provider: str, page: str) -> BasePage:
        """ Return an un-initialized page object of the correct type.

            Input:
                provider [str]: provider to download from
                page [str]: data type searched

            Output:
                obj [BasePage]: page object to download with
        """
        if provider not in self._PROVIDERS:
            raise ValueError("Provider {} not recognized".format(provider))

        return self._PROVIDERS[provider].create_page_obj(page)

    @staticmethod
    def initialize(page_obj: BasePage, ticker: str, currency: str,
                   fname: Union[str, Path] = None, **kwargs) -> BasePage:
        """ Initialize a page object with the correct parameters. If the page
            object is initialized, this call operates as a no-op.
        
            Input:
                page_obj [BasePage]: page object uninitialized
                drow [tuple]: ...
                fname [Union[str, Path]]: file name to load
                **kwargs: parameters for specific page

            Output:
                obj [BasePage]: page object initialized
        """
        if not page_obj.is_inizialized:
            asset = {'ticker': ticker, 'currency': currency}
            page_obj.initialize(asset, fname, kwargs)
        return page_obj

    def bulk_download(self, do_save: bool = True, override_date: bool = False,
                      uid: str = None, provider: str = None, page: str = None,
                      ticker: str = None, override_active: bool = False):
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
        _, upd_list, num = self.downloads_by_uid(provider=provider, page=page,
                                                 uid=uid, ticker=ticker,
                                                 active=active)
        print('We are about to download {} items'.format(num))

        # General variables
        today_string = today_()
        today_dt = today_(string=False)
        q_upd = self._qb.update(self._TABLE, fields=['last_update'])

        for item in upd_list:
            uid, provider, page_name, ticker, currency, upd_freq, last_upd_str = item

            # Check the last update to avoid too frequent updates
            if last_upd_str and not override_date:
                last_upd = datetime.datetime.strptime(last_upd_str, '%Y-%m-%d').date()
                delta_days = (today_dt - last_upd).days
                if delta_days < int(upd_freq):
                    print('[{}: {}] -> {} not updated since last update {} days ago'
                          .format(provider, page_name, ticker, delta_days))
                    continue

            # If the last update check is passed go on with the update
            try:
                page = self.create_page_obj(provider, page_name)
                try:
                    kwargs = self._calc_default_input(provider, ticker, page.table)
                except RuntimeError as e:
                    print(e)
                    continue
                page = self.initialize(page, ticker, currency, **kwargs)

                # Perform download and save results
                try:
                    page.fetch()
                except RuntimeWarning as w:
                    # DownloadFactory throws this error for server return codes != 200
                    print(w)
                    continue
                if do_save is True:
                    page.save()
                else:
                    page.printout()

            except (MissingData, IsNoneError, RuntimeError, RequestException, ValueError) as e:
                print(e)
            else:
                if do_save is True:
                    data_upd = (today_string, provider, page_name, ticker)
                    self._db.execute(q_upd, data_upd, commit=True)


def get_dwnf_glob() -> DownloadFactory:
    """ Returns the pointer to the global Downloads Factory. """
    return DownloadFactory()
