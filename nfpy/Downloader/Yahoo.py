#
# Yahoo Downloader
# Downloads data from Yahoo
#

from abc import abstractmethod
import codecs
from collections import defaultdict
import copy
from io import StringIO
import json
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
    _PAGES = {"HistoricalPrices": "YahooPrices",
              "Financials": "YahooFinancials",
              "Dividends": "YahooDividends",
              "Splits": "YahooSplits"
              }
    _TABLES = {"HistoricalPrices": "YahooPrices",
               "Financials": None,
               "Dividends": "YahooEvents",
               "Splits": "YahooEvents"
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

        t_src = self._TABLES[page]
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

        # Aggregated columns and main data structure
        # Due to stupid Pandas error:
        # NotImplementedError: > 1 ndim Categorical are not supported at this time
        # we have to build a dictionary where to store the data
        all_cols = [c for l in self._COLUMNS[1:] for c in l]
        data_dict = defaultdict(list)
        empty_list = [None] * len(all_cols)

        # Helper functions
        def _new_data_set(_key):
            if _key not in data_dict:
                data_dict[_key] = copy.deepcopy(empty_list)

        def _add_element(_key, _col, _value):
            data_dict[_key][all_cols.index(_col)] = _value

        def _extract_(_yearly, _quarterly):
            for f, p in zip(['A', 'Q'], [_yearly, _quarterly]):
                for item in p:
                    _key = (item['endDate']['fmt'], f)
                    _new_data_set(_key)
                    for k, entry in item.items():
                        if k in ('endDate', 'maxAge'):
                            continue
                        if entry:
                            _add_element(_key, k, entry.get('raw'))

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
        yearly = data['incomeStatementHistory']['incomeStatementHistory']
        quarterly = data['incomeStatementHistoryQuarterly']['incomeStatementHistory']
        _extract_(yearly, quarterly)

        # BALANCE SHEET
        yearly = data['balanceSheetHistory']['balanceSheetStatements']
        quarterly = data['balanceSheetHistoryQuarterly']['balanceSheetStatements']
        _extract_(yearly, quarterly)

        # CASH FLOW
        yearly = data['cashflowStatementHistory']['cashflowStatements']
        quarterly = data['cashflowStatementHistoryQuarterly']['cashflowStatements']
        _extract_(yearly, quarterly)

        # AGGREGATION
        final_data = {}
        i = 0
        for key, value in data_dict.items():
            d = [key[0], key[1]]
            d.extend(value)
            final_data[i] = d
            i = i + 1

        # Add first columns and replace second instance of 'netIncome'
        final_cols = self._COLUMNS[0] + all_cols
        occurrences = [i for i, n in enumerate(final_cols) if n == 'netIncome']
        if len(occurrences) > 1:
            final_cols[occurrences[1]] = 'CFnetIncome'
        df = pd.DataFrame.from_dict(final_data, orient='index', columns=final_cols)
        df.insert(0, 'ticker', self.ticker)

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
        print("CRUMB: {}".format(crumb))
        self.params = {'period1': int(d1), 'period2': int(d2), 'crumb': crumb, 'events': self.event}

    def _parse_csv(self) -> pd.DataFrame:
        # TODO check that columns in the file are correct
        names = self._COLUMNS
        data = StringIO(self._robj.text)
        df = pd.read_csv(data, sep=',', header=None, names=names, skiprows=1)

        # When downloading prices the oldest row is often made of nulls, this is to remove it
        df.replace(to_replace='null', value=pd.np.nan, inplace=True)
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
