#
# Investing Downloader
# Downloads data from investing.com
#

from bs4 import BeautifulSoup
import json
import pandas as pd
from random import randint

from nfpy.Calendar import today
from nfpy.DatatypeFactory import get_dt_glob
from nfpy.Tools import Exceptions as Ex

from .BaseDownloader import BasePage
from .BaseProvider import (BaseProvider, BaseImportItem)
from .DownloadsConf import (InvestingSeriesConf, InvestingCashFlowConf,
                            InvestingBalanceSheetConf, InvestingIncomeStatementConf)


class ClosePricesItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', '1', date, price from InvestingPrices where ticker = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}'), '1900-01-01')"""


class FinancialsItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table}
    (uid, code, date, freq, value) select distinct "{uid}", code, date, freq, value
    from InvestingFinancials where ticker = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}'), '1900-01-01')"""

    def _get_params(self) -> tuple:
        """ Return the correct parameters for the read query. """
        return self._d['ticker'].split('/')[0],


class DividendsItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', dtype, date, value from InvestingEvents
    where ticker = ? and dtype = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}' and dtype = ?), '1900-01-01')"""

    def _get_params(self) -> tuple:
        dt = self._dt.get('dividend')
        if self._incr:
            return self._d['ticker'], dt, dt
        else:
            return self._d['ticker'], dt


class InvestingProvider(BaseProvider):
    """ Class for the Investing.com provider. """

    _PROVIDER = 'Investing'
    _PAGES = {
        'HistoricalPrices': 'InvestingHistoricalPrices',
        'Dividends': 'InvestingDividends',
        'IncomeStatement': 'InvestingIncomeStatement',
        'BalanceSheet': 'InvestingBalanceSheet',
        'CashFlow': 'InvestingCashFlow',
    }
    _IMPORT_ITEMS = {
        'ClosePrices': ClosePricesItem,
        'Dividends': DividendsItem,
        'Financials': FinancialsItem,
    }


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
        'Accept': 'text/html',
        # 'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'X-Requested-With': 'XMLHttpRequest',
    }

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return self._BASE_URL + self._URL_SUFFIX

    def _local_initializations(self, params: dict):
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
    _PARAMS = {
        "curr_id": None,
        "smlID": None,
        "interval_sec": "Daily",
        "st_date": None,
        "end_date": None,
        "sort_col": "date",
        "sort_ord": "ASC",
        "action": "historical_data",
    }
    _MANDATORY = ("curr_id",)

    def _set_default_params(self) -> None:
        self._p = self._PARAMS
        ld = self._fetch_last_data_point()
        self._p.update({
            'curr_id': self.ticker,
            'smlID': str(randint(1000000, 99999999)),
            # 'st_date': pd.to_datetime(ld).strftime('%m/%d/%Y'),
            'st_date': '01/01/2018',
            'end_date': today(fmt='%m/%d/%Y')
        })

    def _local_initializations(self, params: dict):
        """ Local initializations for the single page. """
        if params:
            for p in ['st_date', 'end_date']:
                if p in params:
                    d = params[p]
                    params[p] = pd.to_datetime(d).strftime('%m/%d/%Y')
            self.params = params

    def _parse(self):
        """ Parse the fetched object. """
        dt = []
        soup = BeautifulSoup(self._robj.text, "html.parser")
        t = soup.find('table', {'class': "genTbl closedTbl historicalTbl"})
        if t is None:
            raise RuntimeError('Results table not found in downloaded data')

        d = t.find('tbody')
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
    _TABLE = 'InvestingEvents'
    _URL_SUFFIX = '/equities/MoreDividendsHistory'
    _PARAMS = {'pairID': None, 'last_timestamp': None}
    _MANDATORY = ('pairID', 'last_timestamp')

    def _set_default_params(self) -> None:
        self._p = self._PARAMS
        self._p.update({
            'pairID': self.ticker,
            'last_timestamp': today(fmt='%s')
        })

    def _parse(self):
        if self._robj.text == '':
            raise Ex.MissingData('No data found in downloaded response')

        j = json.loads(self._robj.text)
        soup = BeautifulSoup(j['historyRows'], "html.parser")
        td_list = soup.select('tr > td')
        td_dates = [pd.to_datetime(v['data-value'], unit='s')
                    .strftime('%Y-%m-%d') for v in td_list[::5]]
        td_values = [float(v.text) for v in td_list[1::5]]
        data = list(zip(td_dates, td_values))

        df = pd.DataFrame(data, columns=['date', 'value'])
        df.insert(0, 'ticker', self.ticker)

        code = get_dt_glob().get('dividend')
        df.insert(2, 'dtype', code)
        self._res = df


class InvestingFinancialsBasePage(InvestingBasePage):
    _URL_SUFFIX = '/instruments/Financials/changereporttypeajax?'
    _PARAMS = {'pair_ID': None, 'action': 'change_report_type',
               'report_type': None, 'period_type': None}
    _MANDATORY = ("pair_ID", "period_type")
    _TABLE = 'InvestingFinancials'
    _USE_UPSERT = True
    _REPORT_TYPE = ''

    def _set_default_params(self) -> None:
        self._p = self._PARAMS

        tck = self.ticker.split('/')
        self._p.update({'pair_ID': tck[0],
                        'period_type': tck[1],
                        'report_type': self._REPORT_TYPE})

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
            months = [i.text.split('/')[::-1] for i in h.select('th > div')]
        elif period_type == 'Annual':
            months = [('12', '31')] * 4
        else:
            raise ValueError('Parameter period_type = {} not recognized'
                             .format(self.params['period_type']))
        dates = tuple('-'.join([i, *j]) for i, j in zip(years, months))

        # Get data
        b = soup.find('tbody')
        data = []
        for selection in b.select('tr > td'):
            block = selection.text.split('\n')
            if len(block) > 1:
                continue
            try:
                data.append(float(block[0]))
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

        cols = self._qb.get_fields(self._TABLE)
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
