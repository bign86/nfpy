#
# FRED Downloader
# Downloads data from the FRED DATABASE
#

import pandas as pd
import xml.etree.ElementTree as ET

from nfpy.Calendar import today
from nfpy.Tools import get_conf_glob

from .BaseDownloader import (BasePage, DwnParameter)
from .BaseProvider import (BaseImportItem, BaseProvider)
from .DownloadsConf import FREDSeriesConf


class FREDProvider(BaseProvider):
    _PROVIDER = 'FRED'

    def _filter_todo_downloads(self, todo: set) -> set:
        return todo


class ClosePricesItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', 114, date, value from FREDSeries where ticker = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}' and dtype = 114), '1900-01-01')"""


class AggregatesItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', 114, date, value*1e6 from FREDSeries where ticker = ?"""
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
    _Q_MAX_DATE = "SELECT MAX([date]) FROM FREDSeries WHERE [ticker] = ?"
    _PARAMS = {
        'api_key': DwnParameter('api_key', True, None),
        'series_id': DwnParameter('series_id', True, None),
        'observation_start': DwnParameter('observation_start', False, None),
        'observation_end': DwnParameter('observation_end', False, None),
    }

    def _set_default_params(self) -> None:
        """ Set the starting default of the parameters for the page. """
        # ld = self._fetch_last_data_point((self.ticker,))
        ld = self._DATE0
        self._p = [
            {
                'api_key': get_conf_glob().fred_api_key,
                'series_id': self._ticker,
                'observation_start': pd.to_datetime(ld).strftime('%Y-%m-%d'),
                'observation_end': today(mode='str', fmt='%Y-%m-%d')
            }
        ]

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return self._BASE_URL

    def _local_initializations(self, ext_p: dict) -> None:
        """ Page-dependent initializations of parameters. """
        if ext_p:
            translate = {'start': 'startTime', 'end': 'endTime'}
            p = {}
            for ext_k, ext_v in ext_p.items():
                if ext_k in translate:
                    p[translate[ext_k]] = pd.to_datetime(ext_v).strftime('%Y-%m-%d')
            self._p[0].update(p)

    def _parse(self) -> None:
        """ Parse the fetched object. """
        tree = ET.fromstring(self._robj[0].text)

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
