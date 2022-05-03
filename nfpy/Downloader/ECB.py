#
# ECB Downloader
# Downloads data from the European Central Bank
#

from io import StringIO
import pandas as pd
import re
import requests

from nfpy.Calendar import today
from nfpy.Tools import Exceptions as Ex

from .BaseDownloader import BasePage
from .BaseProvider import BaseImportItem
from .DownloadsConf import ECBSeriesConf


class ClosePricesItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', '1', date, value from ECBSeries where ticker = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}'), '1900-01-01')"""


class ECBBasePage(BasePage):
    """ Base class for all ECB downloads. It cannot be used by itself but the
        derived classes for single download instances should always be used.
    """

    _ENCODING = 'utf-8-sig'
    _PROVIDER = 'ECB'
    _REQ_METHOD = 'get'
    _CRUMB_URL = u'http://sdw.ecb.europa.eu/quickview.do'
    _CRUMB_PATTERN = r'<form name="quickViewForm" method="get" action="\/quickview\.do;jsessionid=(.*?)"'

    def __init__(self, ticker: str):
        super().__init__(ticker)
        self._crumb = None

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return self._BASE_URL.format(self._crumb)

    @property
    def crumburl(self) -> str:
        """ Return the crumb url for the page. """
        return self._CRUMB_URL

    def _fetch_crumb(self) -> str:
        """ Fetch the crumb from ECB. So far this is executed every time a
            new data page is requested.
        """
        res = requests.get(self.crumburl)
        if res.status_code != 200:
            raise requests.HTTPError("Error in downloading the ECB crumb cookie")

        crumb = re.search(self._CRUMB_PATTERN, res.text)
        if crumb is None:
            raise Ex.IsNoneError("Cannot find the crumb cookie from ECB")

        return crumb.group(1)


class SeriesPage(ECBBasePage):
    _PAGE = 'Series'
    _COLUMNS = ECBSeriesConf
    _PARAMS = {
        "trans": "N",
        "start": None,
        "end": None,
        "SERIES_KEY": None,
        "type": "csv"
    }
    _MANDATORY = ("SERIES_KEY",)
    _TABLE = "ECBSeries"
    _BASE_URL = u"http://sdw.ecb.europa.eu/quickviewexport.do;jsessionid={}?"
    _Q_MAX_DATE = "select max(date) from ECBSeries where ticker = ?"

    def _set_default_params(self) -> None:
        self._p = self._PARAMS
        ld = self._fetch_last_data_point((self.ticker,))
        self._p.update({
            'SERIES_KEY': self._ticker,
            'start': pd.to_datetime(ld).strftime('%d-%m-%Y'),
            'end': today(fmt='%d-%m-%Y')
        })

    def _local_initializations(self) -> None:
        """ Local initializations for the single page. """
        p = {}
        if self._ext_p:
            for t in [('start', 'st_date'), ('end', 'end_date')]:
                if t[0] in self._ext_p:
                    d = self._ext_p[t[0]]
                    p[t[1]] = pd.to_datetime(d).strftime('%d-%m-%Y')
            self.params = p
        self._crumb = self._fetch_crumb()

    def _parse(self) -> None:
        """ Parse the fetched object. """
        df = pd.read_csv(
            StringIO(self._robj.text),
            sep=',',
            header=None,
            names=self._COLUMNS,
            skiprows=6,
            index_col=False
        )
        df.insert(0, 'ticker', self.ticker)
        self._res = df
