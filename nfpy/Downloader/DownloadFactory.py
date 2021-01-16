#
# Downloads Factory Class
# Builds download pages, initialize and launch them to
# perform single downloads.
#

import datetime
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
    _Q_MAX_DATE = "select max(date) from {} where ticker = ?"

    def __init__(self):
        self._db = DB.get_db_glob()
        self._qb = DB.get_qb_glob()
        self._downloads_list = None

    def providers(self) -> List:
        """ Return a list of _all_ available providers. """
        return list(self._PROVIDERS.keys())

    # def pages(self, provider: str) -> List:
    #     """ Return a list of _all_ available pages for the given provider. """
    #     return list(self._PROVIDERS[provider].pages)

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
                         uid: str = None, ticker: str = None,
                         active: bool = True) -> tuple:
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

        q_uid = self._qb.select(self._TABLE, fields=fields,
                                keys=k_cond, where=w_cond)
        res = self._db.execute(q_uid, params).fetchall()
        if not res:
            return fields, None, 0

        self._downloads_list = res
        return fields, res, len(res)

    def _calc_default_input(self, prov: str, ticker: str, table: str) -> dict:
        """ Calculates the default input for downloading for the given ticket
            and the given table.

            Input:
                ticker [str]: ticker to be downloaded
                table [str]: destination table

            Output:
                input [dict]: dictionary of the input
        """
        # search for the last available date in DB
        q = self._Q_MAX_DATE.format(table)
        last_date = self._db.execute(q, (ticker,)).fetchone()
        last_date = last_date[0] if last_date[0] is not None else '1990-01-01'

        # If last available data is yesterday skip downloading
        last_dt = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()
        if last_dt >= Cal.last_business(mode='datetime'):
            raise RuntimeError('Already updated')

        return self._PROVIDERS[prov].create_input_dict(last_date)

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
        today_string = Cal.today()
        today_dt = Cal.today(mode='datetime')
        q_upd = self._qb.update(self._TABLE, fields=('last_update',))

        for item in upd_list:
            uid, provider, page_name, ticker, currency, upd_freq, last_upd_str = item

            # Check the last update to avoid too frequent updates
            if last_upd_str and not override_date:
                last_upd = Cal.date_2_datetime(last_upd_str)
                delta_days = (today_dt - last_upd).days
                if delta_days < int(upd_freq):
                    print('[{}: {}] -> {} not updated since last update {} days ago'
                          .format(provider, page_name, ticker, delta_days))
                    continue

            # If the last update check is passed go on with the update
            try:
                print('{}: {} -> {}[{}]'.format(uid, ticker, provider, page_name))
                page = self.create_page_obj(provider, page_name)
                try:
                    kwargs = self._calc_default_input(provider, ticker, page.table)
                except RuntimeError as e:
                    print(e)
                    continue
                page.initialize({'ticker': ticker, 'currency': currency},
                                None, kwargs)

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
