#
# Investing Downloader
# Downloads data from investing.com
#

import json
from typing import Sequence

import pandas as pd
from random import randint
from bs4 import BeautifulSoup

from nfpy.Handlers.Calendar import today
from nfpy.Tools.Exceptions import MissingData
from .BaseDownloader import BasePage
from .BaseProvider import BaseProvider
from .DownloadsConf import InvestingSeriesConf, InvestingCashFlowConf,\
    InvestingBalanceSheetConf, InvestingIncomeStatementConf


class InvestingProvider(BaseProvider):
    """ Class for the Investing.com provider. """

    _PROVIDER = 'Investing'
    _PAGES = {"HistoricalPrices": "InvestingHistoricalPrices",
              "Dividends": "InvestingDividends",
              "IncomeStatement": "InvestingIncomeStatement",
              "BalanceSheet": "InvestingBalanceSheet",
              "CashFlow": "InvestingCashFlow",
              }
    _TABLES = {"HistoricalPrices": "InvestingPrices",
               "IncomeStatement": "InvestingFinancials",
               "BalanceSheet": "InvestingFinancials",
               "CashFlow": "InvestingFinancials"}
    _Q_IMPORT_PRICE = """insert or replace into {dst} (uid, dtype, date, value)
    select '{uid}', '1', ip.date, ip.price from {src} as ip where ip.ticker = ?;"""
    _Q_IMPORT_FINAN = """insert or replace into {dst} (uid, code, date, freq, value)
    select distinct '{uid}', if.code, if.date, if.freq, if.value from {src} as if
    where if.ticker = ? and if.statement = ?;"""

    @staticmethod
    def create_input_dict(last_date: str) -> dict:
        return {"st_date": last_date, "end_date": today(fmt='%Y-%m-%d')}

    def get_import_data(self, data: dict) -> Sequence[Sequence]:
        statements = {'IncomeStatement': 'INC', 'BalanceSheet': 'BAL', 'CashFlow': 'CAS'}
        page = data['page']
        tck = data['ticker'].split('/')[0]
        uid = data['uid']
        t_src = self._TABLES[page]

        if page == 'HistoricalPrices':
            t_dst = self._af.get(uid).ts_table
            query = self._Q_IMPORT_PRICE.format(**{'dst': t_dst, 'src': t_src, 'uid': uid})
            params = (tck,)
        elif page in ('IncomeStatement', 'BalanceSheet', 'CashFlow'):
            t_dst = self._af.get(uid).constituents_table
            st = statements[page]
            query = self._Q_IMPORT_FINAN.format(**{'dst': t_dst, 'src': t_src,
                                                   'uid': uid})
            params = (tck, st)
        else:
            raise ValueError('Page {} for provider Investing unrecognized'.format(page))

        return query, params


class InvestingBasePage(BasePage):
    """ Base class for all Investing downloads. It cannot be used by itself
        but the derived classes for single download instances should always be
        used.
    """

    _ENCODING = 'utf-8-sig'
    _PROVIDER = 'Investing'
    _BASE_URL = u'https://www.investing.com'
    _URL_SUFFIX = ''
    _REQ_METHOD = 'post'
    _HEADER = {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'text/html',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return self._BASE_URL + self._URL_SUFFIX

    def _local_initializations(self):
        """ Local initializations for the single page. """
        pass


class InvestingHistoricalPrices(InvestingBasePage):
    """ Base page for historical downloads.

        NOTE:
        The price is adjusted for splits *NOT* for dividends. We download the
        delta time series with respect to what we have in the database,
        therefore the series must be adjusted for dividends.
        In case of new splits, the series has to be adjusted for them, unless
        the series is downloaded again from scratch.
    """
    _PAGE = 'HistoricalPrices'
    _COLUMNS = InvestingSeriesConf
    _TABLE = 'InvestingPrices'
    _URL_SUFFIX = '/instruments/HistoricalDataAjax'
    _PARAMS = {"curr_id": None, "smlID": None, "interval_sec": "Daily",
               "st_date": None, "end_date": None,
               "sort_col": "date",
               "sort_ord": "ASC", "action": "historical_data"}
    _MANDATORY = ["curr_id"]

    def _local_initializations(self):
        """ Local initializations for the single page. """
        s = self.params.get('st_date', None)
        e = self.params.get('end_date', None)
        try:
            if s:
                s = pd.to_datetime(s).strftime('%m/%d/%Y')
            if e:
                e = pd.to_datetime(e).strftime('%m/%d/%Y')
        except Exception as ex:
            print(ex)
            raise RuntimeError(
                "Error in handling time periods in Investing historical prices download")

        rand_id = str(randint(1000000, 99999999))
        self.params = {'curr_id': self.ticker, 'smlID': rand_id,
                       'st_date': s, 'end_date': e}

    def _parse(self):
        """ Parse the fetched object. """
        dt = []
        soup = BeautifulSoup(self._robj.text, "html.parser")
        t = soup.find('table', {'class': "genTbl closedTbl historicalTbl"})
        if t is None:
            raise RuntimeError('Results table not found in downloaded data')

        d = t.find('tbody')
        # print(d)
        for tr in d.findAll('tr'):
            row = [None] * 6
            i = 0
            for td in tr.findAll('td'):
                if td.has_attr('data-real-value'):
                    val = td['data-real-value'].replace(',', '').replace('-', '')
                    if not val:
                        val = None
                    elif 'M' in val:
                        val = float(val.replace('M', '')) * 1e6
                    elif 'B' in val:
                        val = float(val.replace('B', '')) * 1e9
                    else:
                        val = float(val)
                    row[i] = val
                    i += 1
            dt.append(row)

        df = pd.DataFrame(dt, columns=self._COLUMNS)
        df['date'] = pd.to_datetime(df['date'], unit='s').dt.strftime('%Y-%m-%d')

        df.insert(0, 'ticker', self.ticker)
        self._res = df


class InvestingDividends(InvestingBasePage):
    _PAGE = 'Dividends'
    _COLUMNS = InvestingSeriesConf
    _TABLE = ''
    _URL_SUFFIX = '/equities/MoreDividendsHistory'
    _PARAMS = {"pairID": None, 'last_timestamp': None}
    _MANDATORY = ["pairID", 'last_timestamp']

    def _local_initializations(self):
        """ Local initializations for the single page. """

        self.params = {'pairID': self.ticker, 'last_timestamp': '1286908800'}

    def _parse(self):
        if self._robj.text == '':
            raise MissingData('No data found in downloaded response')

        j = json.loads(self._robj.text)
        soup = BeautifulSoup(j['historyRows'], "html.parser")
        td_list = soup.select('tr > td')
        td_dates = [pd.to_datetime(v['data-value'], unit='s').strftime('%Y-%m-%d')
                    for v in td_list[::5]]
        td_values = [float(v.text) for v in td_list[1::5]]
        data = list(zip(td_dates, td_values))
        df = pd.DataFrame(data, columns=['date', 'value'])
        df.insert(0, 'ticker', self.ticker)
        self._res = df


class InvestingFinancialsBasePage(InvestingBasePage):
    _URL_SUFFIX = '/instruments/Financials/changereporttypeajax?'
    _PARAMS = {"pair_ID": None, 'action': 'change_report_type',
               'report_type': None, 'period_type': None}
    _MANDATORY = ["pair_ID", "period_type"]
    _TABLE = 'InvestingFinancials'
    _USE_UPSERT = True
    _REPORT_TYPE = ''

    def _local_initializations(self):
        """ Local initializations for the single page. """
        p = self.ticker.split('/')
        self.params = {'pair_ID': p[0], 'period_type': p[1],
                       'report_type': self._REPORT_TYPE}

    def _parse(self):
        """ Parse the fetched object. """
        soup = BeautifulSoup(self._robj.text, "html.parser")
        t = soup.find('table', {'class': "genTbl reportTbl"})
        if t is None:
            raise RuntimeError('Data table to parse not found!')

        # Get dates
        period_type = self.params['period_type']
        h = t.find('tr', {'class': "alignBottom"})
        years = [i.text for i in h.select('th > span')][1:]
        if period_type == 'Interim':
            months = [i.text for i in h.select('th > div')]  # [1:]
        elif period_type == 'Annual':
            months = ['31/12'] * 4
        else:
            raise ValueError('Parameter period_type = {} not recognized'
                             .format(self.params['period_type']))
        dates = tuple('/'.join([j, i]) for i, j in zip(years, months))

        # Get data
        b = soup.find('tbody')
        data = []
        for selection in b.select('tr > td'):
            block = selection.text.split('\n')
            if len(block) > 1:
                continue
            try:
                data.append(float(block[0]))  # * 1e6)
            except ValueError:
                if block[0] == '-':
                    data.append(None)
                else:
                    data.append(block[0])
        data = list(zip(*[iter(data)] * 5))

        # Adjust the data structure
        tck, st = self.params['pair_ID'], self.params['report_type']
        freq = 'A' if period_type == 'Annual' else 'Q'
        ccy = self._curr
        data_final = list()
        for tup in data:
            code = self._COLUMNS[tup[0]]
            for d, v in zip(dates, tup[1:]):
                if v is None:
                    continue
                data_final.append((tck, freq, d, ccy, st, code, v))

        cols = ['ticker', 'freq', 'date', 'currency', 'statement', 'code', 'value']
        df = pd.DataFrame(data_final, columns=cols)
        self._res = df


class InvestingIncomeStatement(InvestingFinancialsBasePage):
    _PAGE = 'IncomeStatement'
    _COLUMNS = InvestingIncomeStatementConf
    _REPORT_TYPE = 'INC'


class InvestingBalanceSheet(InvestingFinancialsBasePage):
    _PAGE = 'BalanceSheet'
    _COLUMNS = InvestingBalanceSheetConf
    _REPORT_TYPE = 'BAL'


class InvestingCashFlow(InvestingFinancialsBasePage):
    _PAGE = 'CashFlow'
    _COLUMNS = InvestingCashFlowConf
    _REPORT_TYPE = 'CAS'
