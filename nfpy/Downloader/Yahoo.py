#
# Yahoo Downloader
# Downloads data from Yahoo
#
# NOTES:
# 1. The raw closing price IS NOT adjusted for dividends
# 2. The raw closing price IS adjusted for splits
# 3. The adjusted closing prices ARE adjusted for both dividends and splits
# 4. The dividends ARE adjusted for splits
#
# To be sure to have consistency across raw closing prices and across dividends,
# they must be downloaded again after each split.
#

from abc import abstractmethod
from io import StringIO
import json
import numpy as np
import pandas as pd
import pandas.tseries.offsets as off
import re

import nfpy.Calendar as Cal
from nfpy.Tools import Utilities as Ut

from .BaseDownloader import BasePage
from .BaseProvider import BaseImportItem
from .DownloadsConf import (
    YahooFinancialsConf, YahooFinancialsMapping,
    YahooHistDividendsConf, YahooHistPricesConf, YahooHistSplitsConf
)


class ClosePricesItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', 124, date, close from YahooPrices where ticker = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}' and dtype = 124), '1900-01-01')"""


class FinancialsItem(BaseImportItem):
    _MODE = 'SPLIT'
    _Q_READ = """select distinct '{uid}', statement, code, date, freq, value
    from YahooFinancials where ticker = ?"""
    _Q_WRITE = """insert or replace into {dst_table}
    (uid, code, date, freq, value) values (?, ?, ?, ?, ?)"""

    @staticmethod
    def _clean_data(data: list[tuple]) -> list[tuple]:
        """ Prepare results for import. """
        data_ins = []
        while data:
            item = data.pop(0)

            # Map the field
            try:
                field = YahooFinancialsMapping[item[1]][item[2]]
            except KeyError as ex:
                Ut.print_exc(ex)
                continue

            if field[0] == '':
                continue

            # Adjust the date
            dt = item[3] - off.BDay(10)
            ref = off.BMonthEnd().rollforward(dt)

            # Divide to millions
            value = item[5] * field[2]

            # Build the new tuple
            data_ins.append(
                (item[0], field[0], ref.strftime('%Y-%m-%d'), item[4], value)
            )

        return data_ins


class DividendsItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', 621, date, value from YahooDividends where ticker = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}' and dtype = 621), '1900-01-01')"""


class SplitsItem(BaseImportItem):
    _MODE = 'SPLIT'
    _Q_READ = """select '{uid}', date, value from YahooSplits where ticker = ?"""
    _Q_WRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    values (?, ?, ?, ?)"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}' and dtype = 500), '1900-01-01')"""

    @staticmethod
    def _clean_data(data: list[tuple], *args) -> list[tuple]:
        """ Prepare results for import. """
        data_ins = []
        while data:
            item = data.pop(0)

            # Calculate the factor
            ratio = str(item[2]).split(':')
            value = int(ratio[1]) / int(ratio[0])

            # Build the new tuple
            data_ins.append((item[0], 500, item[1], value))

        return data_ins


class YahooBasePage(BasePage):
    """ Base class for all Yahoo downloads. It cannot be used by itself but the
        derived classes for single download instances should always be used.
    """

    _ENCODING = "utf-8-sig"
    _PROVIDER = "Yahoo"
    _REQ_METHOD = 'get'

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return self._BASE_URL.format(self.ticker)


class FinancialsPage(YahooBasePage):
    _PAGE = 'Financials'
    _COLUMNS = YahooFinancialsConf
    _JSON_PATTERN = r'\s*root\.App\.main\s*=\s*({.*?});\n'
    _BASE_URL = u"https://finance.yahoo.com/quote/{}/financials?"
    _TABLE = "YahooFinancials"

    def _set_default_params(self) -> None:
        pass

    def _local_initializations(self) -> None:
        """ Local initializations for the single page. """
        pass

    def _parse(self) -> None:
        """ Parse the fetched object. """
        json_string = re.search(self._JSON_PATTERN, self._robj.text)
        json_dict = json.loads(json_string.group(1))
        stores = json_dict['context']['dispatcher']['stores']
        data = stores['QuoteSummaryStore']
        if not data:
            msg = f'Data group not found in Yahoo financials for {self.ticker}'
            raise RuntimeError(msg)

        rows = []

        # Helper function for financial statements
        def _extract_f(_p, _data):
            for _item in _data:
                _dt = _item['endDate']['fmt']
                for _field, _entry in _item.items():
                    if _field in ('endDate', 'maxAge'):
                        continue
                    if _entry:
                        _row = _p + (_dt, _field, _entry.get('raw'))
                        rows.append(_row)

        to_download = (
            ('INC', ('incomeStatementHistory', 'incomeStatementHistory'), 'A'),
            ('INC', ('incomeStatementHistoryQuarterly', 'incomeStatementHistory'), 'Q'),
            ('BAL', ('balanceSheetHistory', 'balanceSheetStatements'), 'A'),
            ('BAL', ('balanceSheetHistoryQuarterly', 'balanceSheetStatements'), 'Q'),
            ('CAS', ('cashflowStatementHistory', 'cashflowStatements'), 'A'),
            ('CAS', ('cashflowStatementHistoryQuarterly', 'cashflowStatements'), 'Q'),
        )
        for td in to_download:
            data_list = data[td[1][0]][td[1][1]]
            _extract_f(
                (self._ticker, td[2], self._ext_p['currency'], td[0]),
                data_list
            )

        # Helper function for EPS
        def _extract_e(_p, _data):
            for _item in _data:
                _dt = _item['date']
                for _field, _entry in _item.items():
                    if _field in ('date', 'revenue'):
                        continue
                    elif _field in ('actual', 'estimate'):
                        _field = 'EPS' + _field
                    if _entry:
                        _row = _p + (_dt, _field, _entry.get('raw'))
                        rows.append(_row)

        to_download = (
            ('TS', ('earnings', 'earningsChart', 'quarterly'), 'Q'),
            ('TS', ('earnings', 'financialsChart', 'yearly'), 'A'),
            ('TS', ('earnings', 'financialsChart', 'quarterly'), 'Q'),
        )
        for td in to_download:
            v = td[1]
            data_list = data[v[0]][v[1]][v[2]]
            _extract_e(
                (self._ticker, td[2], self._ext_p['currency'], td[0]),
                data_list
            )

        # Helper function for time series
        def _extract_ts(_p, _field, _data):
            for _item in _data:
                if not _item:
                    continue
                _dt = _item['asOfDate']
                _v = _item['reportedValue']
                if _v:
                    _row = _p + (_dt, _field, _v.get('raw'))
                    rows.append(_row)

        data = stores['QuoteTimeSeriesStore']['timeSeries']
        for k, v in data.items():
            if k == 'timestamp':
                continue
            elif k[:6] == 'annual':
                st = 'A'
                code = k[6:]
            elif k[:8] == 'trailing':
                st = 'TTM'
                code = k[8:]
            else:
                raise ValueError(f'YahooFinancialsPage(): {k} not conformant')
            _extract_ts(
                (self._ticker, st, self._ext_p['currency'], 'TS'),
                code, v
            )

        # Create dataframe
        df = pd.DataFrame.from_records(
            rows,
            columns=self._COLUMNS
        )

        # I want a cleaner version of the _robj for backup purposes
        self._robj = json_string
        self._res = df


class YahooHistoricalBasePage(YahooBasePage):
    """ Base page for historical downloads. """
    _PARAMS = {
        "period1": None,
        "period2": None,
        "interval": "1d",
        "events": None,
        "crumb": None
    }
    _MANDATORY = ("period1", "period2")
    _BASE_URL = u"https://query1.finance.yahoo.com/v7/finance/download/{}?"
    # _BASE_URL = u"https://query1.finance.yahoo.com/v8/finance/chart/{}?"
    _SKIP = [1]

    @property
    @abstractmethod
    def event(self) -> str:
        """ Return the event to complete the request url. """

    def _set_default_params(self) -> None:
        self._p = self._PARAMS
        ld = self._fetch_last_data_point((self.ticker,))
        # We add 2 days instead of 1 since with 1 day of offset the previous
        # split is downloaded again
        start = pd.to_datetime(ld) + pd.DateOffset(days=2)
        self._p.update(
            {
                'period1': str(int(start.timestamp())),
                'period2': Cal.today(mode='str', fmt='%s')
            }
        )

    def _local_initializations(self) -> None:
        """ Local initializations for the single page. """
        p = {'events': self.event}
        if self._ext_p:
            for t in [('start', 'period1'), ('end', 'period2')]:
                if t[0] in self._ext_p:
                    d = self._ext_p[t[0]]
                    p[t[1]] = str(int(pd.to_datetime(d).timestamp()))

        self.params = p

    def _parse_csv(self) -> pd.DataFrame:

        # FIXME: there are errors flying around. This is to intercept them and
        #        understand what is going on.
        try:
            df = pd.read_csv(
                StringIO(self._robj.text),
                sep=',',
                header=None,
                names=self._COLUMNS,
                skiprows=1
            )
        except pd.errors.ParserError as ex:
            print(self._robj.text)
            raise RuntimeError(ex)

        if df.empty:
            raise RuntimeWarning(f'{self.ticker} | no new data downloaded')

        # When downloading prices the oldest row is often made of nulls,
        # this is to remove it
        df.replace(to_replace='null', value=np.nan, inplace=True)
        df.dropna(subset=self._COLUMNS[1:], inplace=True)
        df.insert(0, 'ticker', self.ticker)
        return df


class HistoricalPricesPage(YahooHistoricalBasePage):
    """ Download historical prices. """
    _PAGE = 'HistoricalPrices'
    _COLUMNS = YahooHistPricesConf
    _TABLE = "YahooPrices"
    _Q_MAX_DATE = "select max(date) from YahooPrices where ticker = ?"
    _Q_SELECT = "select * from YahooPrices where ticker = ?"

    @property
    def event(self) -> str:
        return "history"

    def _set_default_params(self) -> None:
        self._p = self._PARAMS
        ld = self._fetch_last_data_point((self.ticker,))
        self._p.update(
            {
                # NOTE: pd.to_datetime(ld).strftime('%s') yields a different output
                'period1': str(int(pd.to_datetime(ld).timestamp())),
                'period2': Cal.today(mode='str', fmt='%s')
            }
        )

    def _parse(self) -> None:
        """ Parse the fetched object. """
        self._res = self._parse_csv()


class DividendsPage(YahooHistoricalBasePage):
    """ Download historical dividends. """
    _PAGE = 'Dividends'
    _COLUMNS = YahooHistDividendsConf
    _TABLE = "YahooDividends"
    _Q_MAX_DATE = "select max(date) from YahooDividends where ticker = ?"
    _Q_SELECT = "select * from YahooDividends where ticker = ?"

    @property
    def event(self) -> str:
        return "dividend"

    def _parse(self) -> None:
        """ Parse the fetched object. """
        self._res = self._parse_csv()


class SplitsPage(YahooHistoricalBasePage):
    """ Download historical splits. """
    _PAGE = 'Splits'
    _COLUMNS = YahooHistSplitsConf
    _TABLE = "YahooSplits"
    _Q_MAX_DATE = "select max(date) from YahooSplits where ticker = ?"
    _Q_SELECT = "select * from YahooSplits where ticker = ?"

    @property
    def event(self) -> str:
        return "split"

    def _parse(self) -> None:
        """ Parse the fetched object. """
        df = self._parse_csv()

        Ut.print_wrn(
            Warning(
                f' >>> New split found for {self.ticker}!\n{df.to_string}'
            )
        )

        self._res = df
