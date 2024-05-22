#
# Nasdaq Downloader
# Downloads data from the Nasdaq website
#

from datetime import datetime
import json
import numpy as np
import pandas as pd

from nfpy.Calendar import today
import nfpy.Tools.Exceptions as Ex

from .BaseDownloader import (BasePage, DwnParameter)
from .BaseProvider import (BaseImportItem, BaseProvider)
from .DownloadsConf import (NasdaqDividendsConf, NasdaqPricesConf)


class NasdaqProvider(BaseProvider):
    _PROVIDER = 'Nasdaq'

    def _filter_todo_downloads(self, todo: set) -> set:
        return todo


class ClosePricesItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', 124, date, close from NasdaqPrices where ticker = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}' and dtype = 124), '1900-01-01')"""


class DividendsItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', 611, date, amount from NasdaqDividends where ticker = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}' and dtype = 611), '1900-01-01')"""


class NasdaqBasePage(BasePage):
    """ Base class for all Nasdaq downloads. It cannot be used by itself but the
        derived classes for single download instances should always be used.
    """

    _ENCODING = "utf-8-sig"
    _PROVIDER = "Nasdaq"
    _REQ_METHOD = 'get'
    _PARAMS = {
        'assetclass': DwnParameter('assetclass', False, 'stocks'),
        'fromdate': DwnParameter('fromdate', True, None),
        'limit': DwnParameter('limit', False, 9999),
        'todate': DwnParameter('todate', True, None),
    }
    _HEADER = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        # 'Host': 'api.nasdaq.com',
        'Accept-Encoding': 'gzip, deflate, br',
    }

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return self._BASE_URL.format(self._ticker)

    def _set_default_params(self) -> None:
        defaults = {}
        for p in self._PARAMS.values():
            if p.default is not None:
                defaults[p.code] = p.default

        ld = self._fetch_last_data_point((self._ticker,))
        defaults.update(
            {
                'fromdate': pd.to_datetime(ld).strftime('%Y-%m-%d'),
                'todate': today(mode='str', fmt='%Y-%m-%d')
            }
        )
        self._p = [defaults]

    def _local_initializations(self, ext_p: dict) -> None:
        """ Local initializations for the single page. """
        if ext_p:
            translate = {'start': 'fromdate', 'end': 'todate'}
            p = {}
            for ext_k, ext_v in ext_p.items():
                if ext_k in translate:
                    p[translate[ext_k]] = pd.to_datetime(ext_v).strftime('%Y-%m-%d')
            self._p[0].update(p)


class HistoricalPricesPage(NasdaqBasePage):
    """ Download historical prices. """

    _BASE_URL = u"https://api.nasdaq.com/api/quote/{}/historical?"
    _PAGE = 'HistoricalPrices'
    _COLUMNS = NasdaqPricesConf
    _TABLE = 'NasdaqPrices'
    _Q_MAX_DATE = "select max(date) from NasdaqPrices where ticker = ?"
    _Q_SELECT = "select * from NasdaqPrices where ticker = ?"

    def _parse(self) -> None:
        j = json.loads(self._robj[0].text)

        message = j['status']['bCodeMessage']
        if message is not None:
            raise ConnectionError(f'Nasdaq(): {self._ticker} | {message[0]["errorMessage"]}')

        count = j['data']['totalRecords']

        if count == 0:
            raise Ex.NoNewDataWarning(f'Nasdaq(): {self._ticker} | no new data downloaded')

        data = j['data']['tradesTable']['rows']
        v = np.empty((count, 6), dtype='object')
        for i, row in enumerate(data):
            v[i, 0] = datetime.strptime(row['date'], '%m/%d/%Y').strftime('%Y-%m-%d')
            v[i, 1] = row['close'].replace('$', '')
            v[i, 2] = row['volume'].replace(',', '')
            v[i, 3] = row['open'].replace('$', '')
            v[i, 4] = row['high'].replace('$', '')
            v[i, 5] = row['low'].replace('$', '')

        df = pd.DataFrame(v, columns=self._COLUMNS)
        df.insert(0, 'ticker', self._ticker)
        self._res = df


class DividendsPage(NasdaqBasePage):
    """ Download dividends. """

    _BASE_URL = u"https://api.nasdaq.com/api/quote/{}/dividends?"
    _PAGE = 'Dividends'
    _COLUMNS = NasdaqDividendsConf
    _TABLE = 'NasdaqDividends'
    _Q_MAX_DATE = "select max(date) from NasdaqDividends where ticker = ?"
    _Q_SELECT = "select * from NasdaqDividends where ticker = ?"

    def _parse(self) -> None:
        j = json.loads(self._robj[0].text)
        data = j['data']['dividends']['rows']

        if data is None:
            raise Ex.NoNewDataWarning(f'Nasdaq(): {self._ticker} | no new data downloaded')

        v = np.empty((len(data), 6), dtype='object')
        to_remove = []
        for i, row in enumerate(data):
            if row['exOrEffDate'] == 'N/A':
                to_remove.append(i)
                continue

            v[i, 0] = datetime.strptime(row['exOrEffDate'], '%m/%d/%Y').strftime('%Y-%m-%d')
            v[i, 1] = row['type']
            v[i, 2] = row['amount'].replace('$', '')

            v[i, 3] = None if row['declarationDate'] == 'N/A' else \
                datetime.strptime(row['declarationDate'], '%m/%d/%Y').strftime('%Y-%m-%d')

            v[i, 4] = None if row['recordDate'] == 'N/A' else \
                datetime.strptime(row['recordDate'], '%m/%d/%Y').strftime('%Y-%m-%d')

            v[i, 5] = None if row['paymentDate'] == 'N/A' else \
                datetime.strptime(row['paymentDate'], '%m/%d/%Y').strftime('%Y-%m-%d')

        v = np.delete(v, to_remove, axis=0)

        df = pd.DataFrame(v, columns=self._COLUMNS)
        df.insert(0, 'ticker', self._ticker)
        self._res = df
