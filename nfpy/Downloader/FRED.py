#
# FRED Downloader
# Downloads data from the FRED DATABASE
#

import pandas as pd
import xml.etree.ElementTree as ET

from nfpy.Calendar import today
from nfpy.Tools import get_conf_glob

from .BaseDownloader import BasePage
from .BaseProvider import BaseImportItem
from .DownloadsConf import FREDSeriesConf


class ClosePricesItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', 114, date, value from FREDSeries where ticker = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}' and dtype = 114), '1900-01-01')"""


class SeriesPage(BasePage):
    """ Base class for all FRED downloads. """

    _ENCODING = 'utf-8-sig'
    _PROVIDER = 'FRED'
    _REQ_METHOD = 'get'
    _PAGE = 'Series'
    _COLUMNS = FREDSeriesConf
    _BASE_URL = u"https://api.stlouisfed.org/fred/series/observations?"
    _TABLE = "FREDSeries"
    _Q_MAX_DATE = "select max(date) from FREDSeries where ticker = ?"
    _PARAMS = {
        'api_key': None,
        'series_id': None,
        'observation_start': None,
        'observation_end': None,
    }
    _MANDATORY = ('api_key', 'series_id')

    def _set_default_params(self) -> None:
        """ Set the starting default of the parameters for the page. """
        self._p = self._PARAMS
        # ld = self._fetch_last_data_point((self.ticker,))
        ld = '1950-01-01'
        self._p.update({
            'api_key': get_conf_glob().fred_api_key,
            'series_id': self._ticker,
            'observation_start': pd.to_datetime(ld).strftime('%Y-%m-%d'),
            'observation_end': today(mode='str', fmt='%Y-%m-%d')
        })

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return self._BASE_URL

    def _local_initializations(self) -> None:
        """ Page-dependent initializations of parameters. """
        if self._ext_p:
            p = {}
            for t in [('start', 'startTime'), ('end', 'endTime')]:
                if t[0] in self._ext_p:
                    d = self._ext_p[t[0]]
                    p[t[1]] = pd.to_datetime(d).strftime('%Y-%m-%d')
            self.params = p

    def _parse(self) -> None:
        """ Parse the fetched object. """
        tree = ET.fromstring(self._robj.text)

        data = []
        for obs in tree.findall('observation'):
            value = obs.attrib['value']
            if value == '.':
                continue
            else:
                value = float(value)

            data.append(
                (
                    obs.attrib['realtime_start'],
                    obs.attrib['realtime_end'],
                    obs.attrib['date'],
                    value
                )
            )

        df = pd.DataFrame(data, columns=self._COLUMNS)
        df.insert(0, 'ticker', self.ticker)
        self._res = df





