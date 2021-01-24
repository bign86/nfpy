#
# Downloads Factory Class
# Builds download pages, initialize and launch them to
# perform single downloads.
#

from requests import RequestException
from typing import List

import nfpy.Calendar as Cal
import nfpy.DB as DB
from nfpy.Tools import (Singleton, Exceptions as Ex)

from .BaseDownloader import BasePage
from .ECB import ECBProvider
from .IB import IBProvider
from .Investing import InvestingProvider
from .Yahoo import YahooProvider


class DownloadFactory(metaclass=Singleton):
    """ Factory to download data from internet. The basic element is the page
        that depends on both provider and ticker downloaded.
    """

    _TABLE = 'Downloads'
    _PROVIDERS = {
        "Yahoo": YahooProvider(),
        "ECB": ECBProvider(),
        "Investing": InvestingProvider(),
        "IB": IBProvider()
    }

    def __init__(self):
        self._db = DB.get_db_glob()
        self._qb = DB.get_qb_glob()
        self._downloads_list = None

    def providers(self) -> List:
        """ Return a list of _all_ available providers. """
        return list(self._PROVIDERS.keys())

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

    def filter_downloads(self, provider: str = None, page: str = None,
                         ticker: str = None, active: bool = True) -> tuple:
        """ Filter download entries.

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
        fields = list(self._qb.get_fields(self._TABLE))
        w_cond = 'active = 1' if active else ''
        k_cond, params = [], ()
        if provider:
            k_cond.append('provider')
            params += (provider,)
        if page:
            k_cond.append('page')
            params += (page,)
        if ticker:
            k_cond.append('ticker')
            params += (ticker,)

        q_uid = self._qb.select(self._TABLE, fields=fields,
                                keys=k_cond, where=w_cond)
        res = self._db.execute(q_uid, params).fetchall()
        if not res:
            return fields, None, 0

        self._downloads_list = res
        return fields, res, len(res)

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
            raise ValueError("Provider {} not recognized".format(provider))
        return prov.create_page_obj(page, ticker)

    def bulk_download(self, do_save: bool = True, override_date: bool = False,
                      provider: str = None, page: str = None,
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
        _, upd_list, num = self.filter_downloads(provider=provider, page=page,
                                                 ticker=ticker,
                                                 active=active)
        print('We are about to download {} items'.format(num))

        # General variables
        today_string = Cal.today()
        today_dt = Cal.today(mode='datetime')
        q_upd = self._qb.update(self._TABLE, fields=('last_update',))

        for item in upd_list:
            provider, page_name, ticker, currency, active, upd_freq, last_upd_str = item

            # Check the last update to avoid too frequent updates
            if last_upd_str and not override_date:
                last_upd = Cal.date_2_datetime(last_upd_str)
                delta_days = (today_dt - last_upd).days
                if delta_days < int(upd_freq):
                    print('[{}: {}] -> {} updated {} days ago'
                          .format(provider, page_name, ticker, delta_days))
                    continue

            # If the last update check is passed go on with the update
            try:
                print('{} -> {}[{}]'.format(ticker, provider, page_name))
                page = self.create_page_obj(provider, page_name, ticker)
                page.initialize(currency=currency)

                # Perform download and save results
                try:
                    page.fetch()
                except RuntimeWarning as w:
                    # DownloadFactory throws this error for codes != 200
                    print(w)
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
                    data_upd = (today_string, provider, page_name, ticker)
                    self._db.execute(q_upd, data_upd, commit=True)


def get_dwnf_glob() -> DownloadFactory:
    """ Returns the pointer to the global Downloads Factory. """
    return DownloadFactory()
