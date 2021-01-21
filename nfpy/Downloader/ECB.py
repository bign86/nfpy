#
# ECB Downloader
# Downloads data from the European Central Bank
#

from io import StringIO
import pandas as pd
import re
import requests
from typing import Sequence

from nfpy.Calendar import today
from nfpy.Tools import Exceptions as Ex

from .BaseDownloader import BasePage
from .BaseProvider import BaseProvider
from .DownloadsConf import ECBSeriesConf


class ECBProvider(BaseProvider):
    """ Class for the European Central Bank provider. """

    _PROVIDER = 'ECB'
    _PAGES = {'Series': ('ECBSeries', 'ECBSeries', 'value', 'price')}
    _Q_IMPORT_PRICE = """insert or replace into {dst} (uid, dtype, date, value)
select '{uid}', '1', ecb.date, ecb.value from {src} as ecb where ecb.ticker = ?;"""

    def get_import_data(self, data: dict) -> Sequence[Sequence]:
        page = data['page']
        uid = data['uid']
        tck = data['ticker']
        t_src = self._PAGES[page][1]

        if page == 'Series':
            t_dst = self._af.get(uid).ts_table
            query = self._Q_IMPORT_PRICE.format(**{'dst': t_dst, 'src': t_src, 'uid': uid})
            params = (tck,)
        else:
            raise ValueError('Page {} for provider ECB unrecognized'.format(page))

        return query, params


class ECBBasePage(BasePage):
    """ Base class for all ECB downloads. It cannot be used by itself
        but the derived classes for single download instances should always be
        used.
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


class ECBSeries(ECBBasePage):
    _PAGE = 'Series'
    _COLUMNS = ECBSeriesConf
    _PARAMS = {"trans": "N",
               "start": None,
               "end": None,
               "SERIES_KEY": None,
               "type": "csv"
               }
    _MANDATORY = ("SERIES_KEY",)
    _TABLE = "ECBSeries"
    _BASE_URL = u"http://sdw.ecb.europa.eu/quickviewexport.do;jsessionid={}?"

    def _set_default_params(self) -> None:
        self._p = self._PARAMS
        ld = self._fetch_last_data_point()
        self._p.update({
            'start': pd.to_datetime(ld).timestamp(),
            'end': today(fmt='%s')
        })

    def _local_initializations(self, params: dict):
        """ Local initializations for the single page. """
        for p in ['start', 'end']:
            try:
                d = params[p]
                params[p] = pd.to_datetime(d).strftime('%d-%m-%Y')
            except KeyError:
                continue
            except Exception as ex:
                print(ex)
                raise RuntimeError("Error in handling time periods for ECB series download")
        self.params = params
        self._crumb = self._fetch_crumb()
        # print("JsessionId: {}".format(crumb))

    def _parse(self):
        """ Parse the fetched object. """
        names = self._COLUMNS
        data = StringIO(self._robj.text)
        df = pd.read_csv(data, sep=',', header=None, names=names, skiprows=5)
        df.insert(0, 'ticker', self.ticker)
        self._res = df
