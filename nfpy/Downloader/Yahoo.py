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
import re

from nfpy.Calendar import today
from nfpy.Tools import Utilities as Ut

from .BaseDownloader import BasePage
from .BaseProvider import BaseImportItem
from .DownloadsConf import (YahooFinancialsConf, YahooHistPricesConf,
                            YahooHistDividendsConf, YahooHistSplitsConf)


class ClosePricesItem(BaseImportItem):
    _Q_READ = "select '{uid}', '1', date, close from YahooPrices where ticker = ?"
    _Q_WRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    values (?,?,?,?)"""
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', '1', date, close from YahooPrices where ticker = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}'), '1900-01-01')"""


class FinancialsItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table}
    (uid, code, date, freq, value) select distinct '{uid}', code, date, freq, value
    from YahooFinancials where ticker = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}'), '1900-01-01')"""


class DividendsItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', dtype, date, value from YahooEvents
    where ticker = ? and dtype = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}' and dtype = ?), '1900-01-01')"""

    def _get_params(self) -> tuple:
        dt = self._dt.get('dividend')
        if self._incr:
            return self._d['ticker'], dt, dt
        else:
            return self._d['ticker'], dt


class SplitsItem(BaseImportItem):
    _Q_READWRITE = """insert or replace into {dst_table} (uid, dtype, date, value)
    select '{uid}', dtype, date, value from YahooEvents
    where ticker = ? and dtype = ?"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}' and dtype = ?), '1900-01-01')"""

    def _get_params(self) -> tuple:
        dt = self._dt.get('split')
        if self._incr:
            return self._d['ticker'], dt, dt
        else:
            return self._d['ticker'], dt


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
        data = json_dict['context']['dispatcher']['stores']['QuoteSummaryStore']
        if not data:
            msg = f'Data group not found in Yahoo financials for {self.ticker}'
            raise RuntimeError(msg)

        rows = []

        # Helper function
        def _extract_(_p, _map, _data):
            for _item in _data:
                _dt = _item['endDate']['fmt']
                for _field, _entry in _item.items():
                    if _field in ('endDate', 'maxAge'):
                        continue
                    if _entry:
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

        to_download = (
            ('INC', 'incomeStatementHistory', 'incomeStatementHistory', 'A'),
            ('INC', 'incomeStatementHistoryQuarterly', 'incomeStatementHistory', 'Q'),
            ('BAL', 'balanceSheetHistory', 'balanceSheetStatements', 'A'),
            ('BAL', 'balanceSheetHistoryQuarterly', 'balanceSheetStatements', 'Q'),
            ('CAS', 'cashflowStatementHistory', 'cashflowStatements', 'A'),
            ('CAS', 'cashflowStatementHistoryQuarterly', 'cashflowStatements', 'Q'),
        )
        for td in to_download:
            _extract_(
                (self._ticker, td[3], self._ext_p['currency'], td[0]),
                YahooFinancialsConf[td[0]],
                data[td[1]][td[2]]
            )

        # Create dataframe
        df = pd.DataFrame.from_records(
            rows,
            columns=self._qb.get_fields(self._TABLE)
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
    _SKIP = [1]

    @property
    @abstractmethod
    def event(self) -> str:
        """ Return the event to complete the request url. """

    def _set_default_params(self) -> None:
        self._p = self._PARAMS
        ld = self._fetch_last_data_point(
            (self.ticker, self._dt.get(self.event))
        )
        # We add 2 days instead of 1 since with 1 day of offset the previous
        # split is downloaded again
        start = pd.to_datetime(ld) + pd.DateOffset(days=2)
        self._p.update(
            {
                'period1': str(int(start.timestamp())),
                'period2': today(mode='str', fmt='%s')
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
        df = pd.read_csv(
            StringIO(self._robj.text),
            sep=',',
            header=None,
            names=self._COLUMNS,
            skiprows=1
        )

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
                # TODO: pd.to_datetime(ld).strftime('%s') yields a different output
                'period1': str(int(pd.to_datetime(ld).timestamp())),
                'period2': today(mode='str', fmt='%s')
            }
        )

    def _parse(self) -> None:
        """ Parse the fetched object. """
        self._res = self._parse_csv()


class DividendsPage(YahooHistoricalBasePage):
    """ Download historical dividends. """
    _PAGE = 'Dividends'
    _COLUMNS = YahooHistDividendsConf
    _TABLE = "YahooEvents"
    _Q_MAX_DATE = "select max(date) from YahooEvents where ticker = ? and dtype = ?"
    _Q_SELECT = "select * from YahooEvents where ticker = ? and dtype = 6"

    @property
    def event(self) -> str:
        return "dividend"

    def _parse(self) -> None:
        """ Parse the fetched object. """
        df = self._parse_csv()
        df.insert(2, 'dtype', self._dt.get('dividend'))
        self._res = df


class SplitsPage(YahooHistoricalBasePage):
    """ Download historical splits. """
    _PAGE = 'Splits'
    _COLUMNS = YahooHistSplitsConf
    _TABLE = "YahooEvents"
    _Q_MAX_DATE = "select max(date) from YahooEvents where ticker = ? and dtype = ?"
    _Q_SELECT = "select * from YahooEvents where ticker = ? and dtype = 5"

    @property
    def event(self) -> str:
        return "split"

    def _parse(self) -> None:
        """ Parse the fetched object. """
        df = self._parse_csv()
        df.insert(2, 'dtype', self._dt.get('split'))

        Ut.print_wrn(
            Warning(
                f' >>> New split found for {self.ticker}!\n{df.to_string}'
            )
        )

        def _calc(x: str) -> float:
            """ Transform splits in adjustment factors """
            factors = x.split(':')
            return float(factors[0]) / float(factors[1])

        df['value'] = df['value'].apply(_calc)
        self._res = df
