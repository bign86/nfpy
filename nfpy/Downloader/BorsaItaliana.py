#
# Borsa Italiana Downloader
# Downloads data from borsaitaliana.it
#

from bs4 import BeautifulSoup
import pandas as pd
from typing import Callable

from .BaseDownloader import BasePage
from .DownloadsConf import BorsaItalianaDividendsConf


class BorsaItalianaBasePage(BasePage):
    """ Base class for all Borsa Italiana downloads. It cannot be used by itself
        but the derived classes for single download instances should always be
        used.
    """

    _ENCODING = 'utf-8-sig'
    _PROVIDER = 'BorsaItaliana'
    _BASE_URL = u'https://www.borsaitaliana.it'
    _URL_SUFFIX = ''
    _REQ_METHOD = 'get'
    _HEADER = {
        'Accept': 'text/html',
        'X-Requested-With': 'XMLHttpRequest',
    }

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return self._BASE_URL + self._URL_SUFFIX.format(isin=self._ticker)

    def _local_initializations(self) -> None:
        """ Local initializations for the single page. """
        pass


class DividendsPage(BorsaItalianaBasePage):
    _PAGE = 'Dividends'
    _COLUMNS = BorsaItalianaDividendsConf
    _TABLE = 'BorsaItalianaDividends'
    _URL_SUFFIX = '/borsa/quotazioni/azioni/elenco-completo-dividendi.html?isin={isin}&page=1&lang=en'
    _Q_MAX_DATE = 'select max(date) from BorsaItalianaDividends where ticker = ?'
    _Q_SELECT = 'select * from BorsaItalianaDividends where ticker = ?'

    def _set_default_params(self) -> None:
        self._p = self._PARAMS

    def _parse(self) -> None:
        """ Parse the fetched object. """
        table = BeautifulSoup(self._robj.text, "html5lib") \
            .find('table', {'class': "m-table -responsive -list -clear-m"}) \
            .find('tbody')
        if table is None:
            raise RuntimeError(f'BorsaItaliana(): Data table to parse not found for {self._ticker}!')

        # Helpers
        def _mutate(_s: str, _cb: Callable) -> str:
            _strip = _s.replace(',', '').strip()
            return _cb(_strip) if _strip else None

        # Get data
        table_data = []
        for row in table.select('tr'):
            data = row.select('td')
            table_data.append(
                (
                    self._ticker,
                    _mutate(data[0].text, str),
                    _mutate(data[1].text, float),
                    _mutate(data[2].text, float),
                    _mutate(data[3].text, str),
                    _mutate(data[4].text, str),
                    _mutate(data[5].text, str),
                    _mutate(data[6].text, str),
                    _mutate(data[7].text, int)
                )
            )

        if len(table_data) == 0:
            raise RuntimeWarning(f'{self._ticker} | no new data downloaded')

        df = pd.DataFrame(
            table_data,
            columns=self._COLUMNS
        )
        self._res = df
