#
# Nasdaq Downloader
# Downloads data from the Nasdaq website
#

from datetime import datetime
import json
import numpy as np
import pandas as pd

from nfpy.Calendar import today

from .BaseDownloader import BasePage
from .BaseProvider import BaseImportItem
from .DownloadsConf import (NasdaqDividendsConf, NasdaqPricesConf)


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
        'assetclass': 'stocks',
        'fromdate': None,
        'limit': 9999,
        'todate': None
    }
    _MANDATORY = ('fromdate', 'todate')
    _HEADER = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        # 'Host': 'api.nasdaq.com',
        'Accept-Encoding': 'gzip, deflate, br',
    }

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return self._BASE_URL.format(self.ticker)

    def _set_default_params(self) -> None:
        self._p = self._PARAMS
        ld = self._fetch_last_data_point((self.ticker,))
        self._p.update(
            {
                'fromdate': pd.to_datetime(ld).strftime('%Y-%m-%d'),
                'todate': today(mode='str', fmt='%Y-%m-%d')
            }
        )

    def _local_initializations(self) -> None:
        """ Local initializations for the single page. """
        p = {}
        if self._ext_p:
            for t in [('start', 'fromdate'), ('end', 'todate')]:
                if t[0] in self._ext_p:
                    d = self._ext_p[t[0]]
                    p[t[1]] = pd.to_datetime(d).strftime('%Y-%m-%d')

        self.params = p


class HistoricalPricesPage(NasdaqBasePage):
    """ Download historical prices. """

    _BASE_URL = u"https://api.nasdaq.com/api/quote/{}/historical?"
    _PAGE = 'HistoricalPrices'
    _COLUMNS = NasdaqPricesConf
    _TABLE = 'NasdaqPrices'
    _Q_MAX_DATE = "select max(date) from NasdaqPrices where ticker = ?"
    _Q_SELECT = "select * from NasdaqPrices where ticker = ?"

    def _parse(self) -> None:
        j = json.loads(self._robj.text)

        message = j['status']['bCodeMessage']
        if message is not None:
            raise ConnectionError(f'Nasdaq(): {self.ticker} | {message[0]["errorMessage"]}')

        count = j['data']['totalRecords']

        if count == 0:
            raise RuntimeWarning(f'Nasdaq(): {self.ticker} | no new data downloaded')

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
        df.insert(0, 'ticker', self.ticker)
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
        j = json.loads(self._robj.text)
        data = j['data']['dividends']['rows']

        if data is None:
            raise RuntimeWarning(f'Nasdaq(): {self.ticker} | no new data downloaded')

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
        df.insert(0, 'ticker', self.ticker)
        self._res = df
