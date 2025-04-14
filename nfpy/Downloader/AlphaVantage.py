
from io import StringIO
import json
import numpy as np
import pandas as pd

from nfpy.Tools import (Exceptions as Ex, get_conf_glob)

from .BaseDownloader import (BasePage, DwnParameter)
from .BaseProvider import (BaseImportItem, BaseProvider)
from .DownloadsConf import (
    AlphaVantageDividendsConf, AlphaVantagePricesConf,
    AlphaVantageSplitsConf, AlphaVantageFinancialsConf
)


class AlphaVantageProvider(BaseProvider):
    _PROVIDER = 'AlphaVantage'

    def _filter_todo_downloads(self, todo: set) -> set:
        return todo


class ClosePricesItem(BaseImportItem):
    _Q_READWRITE = """
    INSERT OR REPLACE INTO [{dst_table}] ([uid], [dtype], [date], [value])
    SELECT '{uid}', 114, [date], [close]
    FROM [AlphaVantagePrices] WHERE [ticker] = ?"""
    _Q_INCR = """ AND [date] > IFNULL(
        (SELECT MAX([date]) FROM [{dst_table}]
        WHERE [uid] = '{uid}' AND [dtype] = 114),
        '1900-01-01')"""


class DividendsItem(BaseImportItem):
    _Q_READWRITE = """
    INSERT OR REPLACE INTO [{dst_table}] ([uid], [dtype], [date], [value])
    SELECT '{uid}', 611, [date], [value]
    FROM [YahooDividends] WHERE [ticker] = ?"""
    _Q_INCR = """ AND [date] > IFNULL(
        (SELECT MAX([date]) FROM [{dst_table}]
        WHERE [uid] = '{uid}' AND [dtype] = 611),
        '1900-01-01')"""


class SplitsItem(BaseImportItem):
    _MODE = 'SPLIT'
    _Q_READ = """SELECT '{uid}', [date], [value]
    FROM [YahooSplits] WHERE [ticker] = ?"""
    _Q_WRITE = """
        INSERT OR REPLACE INTO [{dst_table}] ([uid], [dtype], [date], [value])
        VALUES (?, ?, ?, ?)"""
    _Q_INCR = """ AND [date] > IFNULL(
        (SELECT MAX([date]) FROM [{dst_table}]
        WHERE [uid] = '{uid}' AND [dtype] = 500),
        '1900-01-01')"""


class AlphaVantageBasePage(BasePage):
    """ Base class for all AlphaVantage downloads. It cannot be used by itself
        but the derived classes for single download instances should always
        be used.
    """
    _ENCODING = 'utf-8-sig'
    _PROVIDER = 'AlphaVantage'
    _REQ_METHOD = 'get'
    _BASE_URL = 'https://www.alphavantage.co/query?'

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return self._BASE_URL

    @staticmethod
    def get_api_key() -> str:
        """ Return the API key for the download. """
        return get_conf_glob().alpha_vantage_api_key

    def _set_default_params(self) -> None:
        """ Set the starting default of the parameters for the page. """
        # Collect defaults
        defaults = {
            p.code: p.default
            for p in self._PARAMS.values()
            if p.default is not None
        }

        defaults['symbol'] = self._ticker
        defaults['apikey'] = self.get_api_key()
        self._p = [defaults]

    def _local_initializations(self, ext_p: dict) -> None:
        """ Local initializations for the single page. """
        pass


class HistoricalPricesPage(AlphaVantageBasePage):
    _PARAMS = {
        'function': DwnParameter('function', True, 'TIME_SERIES_DAILY'),
        'symbol': DwnParameter('symbol', True, None),
        'outputsize': DwnParameter('outputsize', False, 'full'),
        'apikey': DwnParameter('apikey', True, None),
    }
    _PAGE = 'HistoricalPrices'
    _COLUMNS = AlphaVantagePricesConf
    _TABLE = 'AlphaVantagePrices'

    def _parse(self) -> None:
        j = json.loads(self._robj[0].text)["Time Series (Daily)"]
        df = pd.read_json(
            StringIO(json.dumps(j)),
            orient='index'
        )
        df.reset_index(inplace=True)
        df.columns = self._COLUMNS
        df['date'] = df.date.dt.date

        if df.empty:
            raise Ex.NoNewDataWarning(f'{self._ticker} | no new data downloaded')

        df.replace(to_replace='null', value=np.nan, inplace=True)
        df.insert(0, 'ticker', self._ticker)
        self._res = df


class DividendsPage(AlphaVantageBasePage):
    _PARAMS = {
        'function': DwnParameter('function', True, 'DIVIDENDS'),
        'symbol': DwnParameter('symbol', True, None),
        'apikey': DwnParameter('apikey', True, None),
    }
    _PAGE = 'Dividends'
    _COLUMNS = AlphaVantageDividendsConf
    _TABLE = 'AlphaVantageDividends'

    def _parse(self) -> None:
        j = json.loads(self._robj[0].text)
        sym = j['symbol']
        df = pd.read_json(
            StringIO(json.dumps(j['data']))
        )
        df.columns = self._COLUMNS

        if df.empty:
            raise Ex.NoNewDataWarning(f'{sym} | no new data downloaded')

        df.replace(to_replace='None', value=None, inplace=True)
        df.insert(0, 'ticker', sym)
        self._res = df


class SplitsPage(AlphaVantageBasePage):
    _PARAMS = {
        'function': DwnParameter('function', True, 'SPLITS'),
        'symbol': DwnParameter('symbol', True, None),
        'apikey': DwnParameter('apikey', True, None),
    }
    _PAGE = 'Splits'
    _COLUMNS = AlphaVantageSplitsConf
    _TABLE = 'AlphaVantageSplits'

    def _parse(self) -> None:
        j = json.loads(self._robj[0].text)["data"]
        sym = j['symbol']
        df = pd.read_json(
            StringIO(json.dumps(j['data']))
        )
        df.columns = self._COLUMNS

        if df.empty:
            raise Ex.NoNewDataWarning(f'{sym} | no new data downloaded')

        df.replace(to_replace='None', value=None, inplace=True)
        df.insert(0, 'ticker', sym)
        self._res = df


class FinancialsBasePage(AlphaVantageBasePage):
    _PARAMS = {
        'function': DwnParameter('function', True, 'INCOME_STATEMENT'),
        'symbol': DwnParameter('symbol', True, None),
        'apikey': DwnParameter('apikey', True, None),
    }
    _PAGE = 'IncomeStatement'
    _STATEMENT = ''
    _COLUMNS = AlphaVantageFinancialsConf
    _TABLE = 'AlphaVantageFinancials'

    def _parse(self) -> None:
        j = json.loads(self._robj[0].text)
        sym = j['symbol']
        data = []

        def _unravel_data(_src: dict, _f: str, _d: list) -> None:
            for _item in _src:
                _date = _item['fiscalDateEnding']
                _ccy = _item['reportedCurrency']
                for _k, _v in _item.items():
                    if _k in ('fiscalDateEnding', 'reportedCurrency'):
                        continue
                    _d.append((sym, _f, _date, _ccy, self._STATEMENT, _k, _v))

        annual = j.get('annualReports', [])
        if annual:
            _unravel_data(annual, 'Y', data)

        quarterly = j.get('quarterlyReports', [])
        if quarterly:
            _unravel_data(quarterly, 'Q', data)

        df = pd.DataFrame(data, columns=self._COLUMNS)

        if df.empty:
            raise Ex.NoNewDataWarning(f'{self._ticker} | no new data downloaded')

        self._res = df


class IncomeStatementPage(FinancialsBasePage):
    _PARAMS = {
        'function': DwnParameter('function', True, 'INCOME_STATEMENT'),
        'symbol': DwnParameter('symbol', True, None),
        'apikey': DwnParameter('apikey', True, None),
    }
    _PAGE = 'IncomeStatement'
    _STATEMENT = 'INC'


class BalanceSheetPage(FinancialsBasePage):
    _PARAMS = {
        'function': DwnParameter('function', True, 'BALANCE_SHEET'),
        'symbol': DwnParameter('symbol', True, None),
        'apikey': DwnParameter('apikey', True, None),
    }
    _PAGE = 'BalanceSheet'
    _STATEMENT = 'BAL'


class CashFlowPage(FinancialsBasePage):
    _PARAMS = {
        'function': DwnParameter('function', True, 'CASH_FLOW'),
        'symbol': DwnParameter('symbol', True, None),
        'apikey': DwnParameter('apikey', True, None),
    }
    _PAGE = 'CashFlow'
    _STATEMENT = 'CAS'



[{
    "code": 200,
    "body": {
        "id": "fc6acd0f-355f-49d8-9a9e-6720c035b5de",
        "name": "LinkClick",
        "time": "2025-03-20T13:39:52.471Z",
        "user_id": "05004b12-2e36-418c-ac1f-df5f336272d9",
        "view_id": "3ea0f390-9003-42ca-b55c-648e25df89ed",
        "session_id": "1b46875c-dcc2-4a77-a540-b4bc0cc36168",
        "segments": [],
        "properties": {
            "dest_url": "https://www.marketwatch.com/investing/index/sp500.352020/downloaddatapartial?startdate=02/17/2025%2000:00:00&enddate=03/19/2025%2023:59:59&daterange=d30&frequency=p1d&csvdownload=true&downloadpartial=false&newdates=false&countrycode=xx",
            "client": {
                "domain": "www.marketwatch.com",
                "referrer": "https://www.marketwatch.com/investing/index/sp500.352020?countrycode=xx",
                "title": "Download SP500.352020 Data | S&P 500 Pharmaceuticals Industry Index Price Data | MarketWatch",
                "type": "web",
                "url": "https://www.marketwatch.com/investing/index/sp500.352020/download-data?countrycode=xx&mod=mw_quote_tab",
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15 PermutiveWebSDK/v20.36.1"
            }
        },
        "cohorts": []
    }
}]

