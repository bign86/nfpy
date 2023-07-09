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

from .BaseDownloader import (BasePage, DwnParameter)
from .BaseProvider import BaseImportItem
from .DownloadsConf import ECBSeriesConf


class ClosePricesItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', 114, date, value from ECBSeries where ticker = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}' and dtype = 114), '1900-01-01')"""


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
        'trans': DwnParameter('trans', False, 'N'),
        'start': DwnParameter('start', False, None),
        'end': DwnParameter('end', False, None),
        'SERIES_KEY': DwnParameter('SERIES_KEY', True, None),
        'type': DwnParameter('type', False, "csv"),
    }
    _TABLE = "ECBSeries"
    _BASE_URL = u"http://sdw.ecb.europa.eu/quickviewexport.do;jsessionid={}?"
    _Q_MAX_DATE = "select max(date) from ECBSeries where ticker = ?"

    def _set_default_params(self) -> None:
        defaults = {}
        for p in self._PARAMS.values():
            if p.default is not None:
                defaults[p.code] = p.default

        ld = self._fetch_last_data_point((self._ticker,))
        defaults.update({
            'SERIES_KEY': self._ticker,
            'start': pd.to_datetime(ld).strftime('%d-%m-%Y'),
            'end': today(fmt='%d-%m-%Y')
        })
        self._p = [defaults]

    def _local_initializations(self, ext_p: dict) -> None:
        """ Local initializations for the single page. """
        if ext_p:
            translate = {'start': 'st_date', 'end': 'end_date'}
            p = {}
            for ext_k, ext_v in ext_p.items():
                if ext_k in translate:
                    p[translate[ext_k]] = pd.to_datetime(ext_v).strftime('%d-%m-%Y')
            self._p[0].update(p)

        self._crumb = self._fetch_crumb()

    def _parse(self) -> None:
        """ Parse the fetched object. """
        df = pd.read_csv(
            StringIO(self._robj[0].text),
            sep=',',
            header=None,
            names=self._COLUMNS,
            skiprows=6,
            index_col=False
        )

        if df.empty:
            raise RuntimeWarning(f'{self._ticker} | no new data downloaded')

        df.drop(columns=self._COLUMNS[-1], inplace=True)
        df.insert(0, 'ticker', self._ticker)
        self._res = df
