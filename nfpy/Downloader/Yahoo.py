#
# Yahoo Downloader
# Downloads data from Yahoo
#

from abc import abstractmethod
import codecs
from io import StringIO
import json
import numpy as np
import pandas as pd
import re
import requests
from typing import Sequence

from nfpy.Calendar import today
from nfpy.Tools import Exceptions as Ex

from .BaseDownloader import BasePage
from .BaseProvider import BaseProvider
from .DownloadsConf import (YahooFinancialsConf, YahooHistPricesConf,
                            YahooHistDividendsConf, YahooHistSplitsConf)


class YahooProvider(BaseProvider):
    """ Class for the Yahoo Finance provider. """

    _PROVIDER = 'Yahoo'
    _PAGES = {'HistoricalPrices': ('YahooPrices',
                                   'YahooPrices',
                                   'close',
                                   'price'),
              'Financials': ('YahooFinancials',
                             None,
                             'financials',
                             'financials'),
              'Dividends': ('YahooDividends',
                            'YahooEvents',
                            'value',
                            'dividend'),
              'Splits': ('YahooSplits',
                         'YahooEvents',
                         'value',
                         'split')
              }
    _Q_IMPORT_PRICE = """insert or replace into {dst} (uid, dtype, date, value)
    select '{uid}', '1', yp.date, yp.close from {src} as yp where yp.ticker = ?;"""
    _Q_IMPORT_EVENT = """insert or replace into {dst} (uid, dtype, date, value)
    select '{uid}', ye.dtype, ye.date, ye.value from {src} as ye
    where ye.ticker = ? and ye.dtype = ?;"""

    @staticmethod
    def create_input_dict(last_date: str) -> dict:
        return {'period1': last_date, 'period2': today(fmt='%Y-%m-%d')}

    def get_import_data(self, data: dict) -> Sequence[Sequence]:
        page = data['page']
        tck = data['ticker']
        uid = data['uid']

        t_src = self._PAGES[page][1]
        t_dst = self._af.get(uid).ts_table

        if page == 'HistoricalPrices':
            query = self._Q_IMPORT_PRICE
            params = (tck,)
        elif page in ('Splits', 'Dividends'):
            code = self._dt.get(data['tgt_datatype'])
            query = self._Q_IMPORT_EVENT
            params = (tck, code)
        else:
            raise ValueError('Page {} for provider Yahoo unrecognized'.format(page))

        query = query.format(**{'dst': t_dst, 'src': t_src, 'uid': uid})
        return query, params


class YahooBasePage(BasePage):
    """ Base class for all Yahoo downloads. It cannot be used by itself but the
        derived classes for single download instances should always be used.
    """

    _ENCODING = "utf-8-sig"
    _PROVIDER = "Yahoo"
    _CRUMB_URL = u"https://finance.yahoo.com/quote/{}"
    _CRUMB_PATTERN = r'"CrumbStore"\s*:\s*\{\s*"crumb"\s*:\s*"(.*?)"\s*\}'
    _REQ_METHOD = 'get'

    def __init__(self):
        super().__init__()
        self._crumb = None

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return self._BASE_URL.format(self.ticker)

    @property
    def crumburl(self) -> str:
        """ Return the crumb url for the page. """
        return self._CRUMB_URL.format(self.ticker)

    def _fetch_crumb(self) -> str:
        """ Fetch the crumb from Yahoo. So far this is executed every time a
            new data page is requested.
        """
        res = requests.get(self.crumburl)  # , params={'p': self.ticker})
        if res.status_code != 200:
            raise requests.HTTPError("Error in downloading the Yahoo crumb cookie")

        crumb = re.search(self._CRUMB_PATTERN, res.text)
        if crumb is None:
            raise Ex.IsNoneError("Cannot find the crumb cookie from Yahoo")

        self._jar = res.cookies
        return codecs.decode(crumb.group(1), 'unicode_escape')


class YahooFinancials(YahooBasePage):
    _PAGE = 'Financials'
    _COLUMNS = YahooFinancialsConf
    _JSON_PATTERN = r'\s*root\.App\.main\s*=\s*({.*?});\n'
    _BASE_URL = u"https://finance.yahoo.com/quote/{}/financials?"
    _TABLE = "YahooFinancials"

    def _local_initializations(self):
        """ Local initializations for the single page. """
        pass

    @staticmethod
    def _get_field(it, k):
        val = None
        f = it.get(k)
        if f:
            val = f.get('raw')
        return val

    def _parse(self):
        """ Parse the fetched object. """
        json_string = re.search(self._JSON_PATTERN, self._robj.text)
        json_dict = json.loads(json_string.group(1))
        data = json_dict['context']['dispatcher']['stores']['QuoteSummaryStore']
        if not data:
            raise RuntimeError('Data group not found in Yahoo financials for {}'
                               .format(self.ticker))

        rows = []

        # Helper function
        def _extract_(_p, _map, _data):
            for _item in _data:
                _dt = _item['endDate']['fmt']
                for _field, _entry in _item.items():
                    if _field in ('endDate', 'maxAge'):
                        continue
                    if _entry:
                        # _row = _p + (_dt, _map[_field], _entry.get('raw'))
                        _row = _p + (_dt, _field, _entry.get('raw'))
                        rows.append(_row)

        # ------------------------------
        #          EARNINGS
        # ------------------------------
        # earn_chart = data['earnings']['earningsChart']
        # quarter = earn_chart['quarterly']
        # for item in quarter:
        #    date = pd.Period(item['date'], freq='Q').strftime('%Y-%m-%d')
        #    key = (date, 'Q')
        #    _new_data_set(key)
        #    _add_element(key, 'earningsActual', item['actual'].get('raw'))
        #    _add_element(key, 'earningsEstimate', item['estimate'].get('raw'))

        # INCOME STATEMENT
        hash_map = YahooFinancialsConf['INC']

        yearly = data['incomeStatementHistory']['incomeStatementHistory']
        p = (self._ticker, 'A', self._curr, 'INC')
        _extract_(p, hash_map, yearly)

        quarterly = data['incomeStatementHistoryQuarterly']['incomeStatementHistory']
        p = (self._ticker, 'Q', self._curr, 'INC')
        _extract_(p, hash_map, quarterly)

        # BALANCE SHEET
        hash_map = YahooFinancialsConf['BAL']

        yearly = data['balanceSheetHistory']['balanceSheetStatements']
        p = (self._ticker, 'A', self._curr, 'BAL')
        _extract_(p, hash_map, yearly)

        quarterly = data['balanceSheetHistoryQuarterly']['balanceSheetStatements']
        p = (self._ticker, 'Q', self._curr, 'BAL')
        _extract_(p, hash_map, quarterly)

        # CASH FLOW
        hash_map = YahooFinancialsConf['CAS']

        yearly = data['cashflowStatementHistory']['cashflowStatements']
        p = (self._ticker, 'A', self._curr, 'CAS')
        _extract_(p, hash_map, yearly)

        quarterly = data['cashflowStatementHistoryQuarterly']['cashflowStatements']
        p = (self._ticker, 'Q', self._curr, 'CAS')
        _extract_(p, hash_map, quarterly)

        # Create dataframe
        cols = ['ticker', 'freq', 'currency', 'statement', 'date', 'code', 'value']
        df = pd.DataFrame.from_records(rows, columns=cols)

        # I want a cleaner version of the _robj for backup purposes
        self._robj = json_string
        self._res = df


class YahooHistoricalBasePage(YahooBasePage):
    """ Base page for historical downloads.

        NOTE:
        The close price is adjusted for splits *NOT* for dividends. The adjusted
        close is corrected also for dividends. We download the delta time series
        with respect to what we have in the database, therefore the adjusted
        series cannot be relied upon.
        In case of new splits, the series has to be adjusted for them, unless
        the series is downloaded again from scratch.
    """
    _PARAMS = {"period1": None, "period2": None, "interval": "1d",
               "events": None, "crumb": None}
    _MANDATORY = ["period1", "period2"]
    _BASE_URL = u"https://query1.finance.yahoo.com/v7/finance/download/{}?"
    _SKIP = [1]

    @property
    @abstractmethod
    def event(self) -> str:
        """ Return the event to complete the request url. """

    def _local_initializations(self):
        """ Local initializations for the single page. """
        try:
            d1 = pd.to_datetime(self.params['period1']).timestamp()
            d2 = pd.to_datetime(self.params['period2']).timestamp()
        except Exception as ex:
            print(ex)
            raise RuntimeError("Error in converting dates for Yahoo historical prices download")

        crumb = self._fetch_crumb()
        # print("CRUMB: {}".format(crumb))
        self.params = {'period1': int(d1), 'period2': int(d2),
                       'crumb': crumb, 'events': self.event}

    def _parse_csv(self) -> pd.DataFrame:
        names = self._COLUMNS
        data = StringIO(self._robj.text)
        df = pd.read_csv(data, sep=',', header=None, names=names, skiprows=1)

        # When downloading prices the oldest row is often made of nulls,
        # this is to remove it
        df.replace(to_replace='null', value=np.nan, inplace=True)
        df.dropna(subset=names[1:], inplace=True)
        df.insert(0, 'ticker', self.ticker)
        return df


class YahooPrices(YahooHistoricalBasePage):
    """ Download historical prices. """
    _PAGE = 'HistoricalPrices'
    _COLUMNS = YahooHistPricesConf
    _TABLE = "YahooPrices"

    @property
    def event(self) -> str:
        return "history"

    def _parse(self):
        """ Parse the fetched object. """
        self._res = self._parse_csv()


class YahooDividends(YahooHistoricalBasePage):
    """ Download historical dividends. """
    _PAGE = 'Dividends'
    _COLUMNS = YahooHistDividendsConf
    _TABLE = "YahooEvents"

    @property
    def event(self) -> str:
        return "dividend"

    def _parse(self):
        """ Parse the fetched object. """
        df = self._parse_csv()
        df.insert(2, 'dtype', self._dt.get('dividend'))
        self._res = df


class YahooSplits(YahooHistoricalBasePage):
    """ Download historical splits. """
    _PAGE = 'Splits'
    _COLUMNS = YahooHistSplitsConf
    _TABLE = "YahooEvents"

    @property
    def event(self) -> str:
        return "split"

    def _parse(self):
        """ Parse the fetched object. """
        df = self._parse_csv()
        df.insert(2, 'dtype', self._dt.get('split'))

        def _calc(x: str) -> float:
            """ Transform splits in adjustment factors """
            factors = x.split('/')
            return float(factors[0]) / float(factors[1])

        df['value'] = df['value'].apply(_calc)
        self._res = df
