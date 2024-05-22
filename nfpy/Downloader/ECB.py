#
# ECB Downloader
# Downloads data from the European Central Bank
#

from io import StringIO
import pandas as pd

import nfpy.Tools.Exceptions as Ex

from .BaseDownloader import (BasePage, DwnParameter)
from .BaseProvider import (BaseImportItem, BaseProvider)
from .DownloadsConf import (ECBAggregatesConf, ECBExrConf,
                            ECBRatesConf, ECBYieldsConf, ECBSeriesConf)


class ECBProvider(BaseProvider):
    _PROVIDER = 'ECB'

    def _filter_todo_downloads(self, todo: set) -> set:
        return todo


class ECBBaseItem(BaseImportItem):
    _MODE = 'SPLIT'
    _Q_WRITE = """insert or replace into [{dst_table}] (uid, dtype, date, value)
    values (?, ?, ?, ?)"""
    _Q_INCR = """ and time_period > iif(freq == 'Q',
    substr(ifnull((select max(date) from [{dst_table}] where uid = '{uid}'),
    '1900-Q1'),1,7),substr(ifnull((select max(date) from [{dst_table}]
    where uid = '{uid}'),'1900'),1,4))"""


class AggregatesItem(ECBBaseItem):
    _Q_READWRITE = """insert or replace into [{dst_table}] ([uid], dtype, date, value)
    select '{uid}', 114, time_period, obs_value from ECBAggregates where ticker = ?"""
    # Note: the obs_vallue is multiplied by 1e6 to account for the Millions EUR
    _Q_READ = """select '{uid}', 114, time_period, obs_value*1e6 from [ECBAggregates] where ticker = ?"""


class FxItem(ECBBaseItem):
    _Q_READWRITE = """insert or replace into [{dst_table}] ([uid], dtype, date, value)
    select '{uid}', 114, time_period, obs_value from ECBExr where ticker = ?"""
    _Q_READ = """select '{uid}', 114, time_period, obs_value from [ECBExr] where ticker = ?"""


class RatesItem(ECBBaseItem):
    _Q_READWRITE = """insert or replace into [{dst_table}] ([uid], dtype, date, value)
    select '{uid}', 114, time_period, obs_value from ECBRates where ticker = ?"""
    _Q_READ = """select '{uid}', 114, time_period, obs_value from [ECBRates] where ticker = ?"""


class YieldsItem(ECBBaseItem):
    _Q_READWRITE = """insert or replace into [{dst_table}] ([uid], dtype, date, value)
    select '{uid}', 114, time_period, obs_value from ECBYields where ticker = ?"""
    _Q_READ = """select '{uid}', 114, time_period, obs_value from [ECBYields] where ticker = ?"""


class ECBBasePage(BasePage):
    """ Base class for all ECB downloads. It cannot be used by itself but the
        derived classes for single download instances should always be used.
    """

    _ENCODING = 'utf-8-sig'
    _PROVIDER = 'ECB'
    _REQ_METHOD = 'get'
    _BASE_URL = u"https://data-api.ecb.europa.eu/service/data/{dataset}/{series_key}?"
    _PARAMS = {
        'updatedAfter': DwnParameter('updatedAfter', False, None),
        'format': DwnParameter('format', False, 'csvdata'),
        'startPeriod': DwnParameter('startPeriod', False, None),
        'endPeriod': DwnParameter('endPeriod', False, None),
        'detail': DwnParameter('detail', False, 'dataonly')
    }

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        request = self._ticker.split('.', maxsplit=1)
        return self._BASE_URL.format(
            dataset=request[0], series_key=request[1]
        )

    def _set_default_params(self) -> None:
        defaults = {}
        for p in self._PARAMS.values():
            if p.default is not None:
                defaults[p.code] = p.default

        ld = self._fetch_last_data_point((self._ticker,))
        date = pd.to_datetime(ld).strftime('%Y-%m-%d')
        defaults.update({'updatedAfter': f'{date}T00:00:00+00:00'})
        self._p = [defaults]

    def _local_initializations(self, ext_p: dict) -> None:
        """ Local initializations for the single page. """
        if ext_p:
            translate = {'start': 'startPeriod', 'end': 'endPeriod'}
            p = {}
            for ext_k, ext_v in ext_p.items():
                if ext_k in translate:
                    p[translate[ext_k]] = pd.to_datetime(ext_v).strftime('%Y-%m-%d')
            self._p[0].update(p)

    def _parse(self) -> None:
        """ Parse the fetched object. """
        df = pd.read_csv(
            StringIO(self._robj[0].text),
            sep=',',
            header=0,
            names=self._COLUMNS,
            index_col=False
        )

        if df.empty:
            raise Ex.NoNewDataWarning(f'{self._ticker} | no new data downloaded')

        df.drop(columns='action', inplace=True)
        self._res = df


class SeriesPage(ECBBasePage):
    _PAGE = 'Series'
    _COLUMNS = ECBSeriesConf
    _TABLE = "ECBSeries"
    _Q_MAX_DATE = "select max(date) from ECBSeries where ticker = ?"


class AggregatesPage(ECBBasePage):
    _PAGE = 'Aggregates'
    _COLUMNS = ECBAggregatesConf
    _TABLE = "ECBAggregates"
    _Q_MAX_DATE = "select max(time_period) from ECBAggregates where ticker = ?"


class ExrPage(ECBBasePage):
    _PAGE = 'Exr'
    _COLUMNS = ECBExrConf
    _TABLE = "ECBExr"
    _Q_MAX_DATE = "select max(time_period) from ECBExr where ticker = ?"


class RatesPage(ECBBasePage):
    _PAGE = 'Rates'
    _COLUMNS = ECBRatesConf
    _TABLE = "ECBRates"
    _Q_MAX_DATE = "select max(time_period) from ECBRates where ticker = ?"


class YieldsPage(ECBBasePage):
    _PAGE = 'Yields'
    _COLUMNS = ECBYieldsConf
    _TABLE = "ECBYields"
    _Q_MAX_DATE = "select max(time_period) from ECBYields where ticker = ?"
