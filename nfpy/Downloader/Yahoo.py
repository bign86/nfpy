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
import time

import nfpy.Calendar as Cal
import nfpy.IO.Utilities as Ut
from nfpy.Tools import Exceptions as Ex

from .BaseDownloader import (BasePage, DwnParameter)
from .BaseProvider import (BaseImportItem, BaseProvider)
from .DownloadsConf import (
    YahooFinancialsConf, YahooFinancialsMapping, YahooFinancialsDownloadList,
    YahooHistDividendsConf, YahooHistPricesConf, YahooHistSplitsConf
)


class YahooProvider(BaseProvider):
    _PROVIDER = 'Yahoo'

    def _filter_todo_downloads(self, todo: set) -> set:
        return todo


class ClosePricesItem(BaseImportItem):
    _Q_READWRITE = """
    INSERT OR REPLACE INTO [{dst_table}] ([uid], [dtype], [date], [value])
    SELECT '{uid}', 124, [date], [close]
    FROM [YahooPrices] WHERE [ticker] = ?"""
    _Q_INCR = """ AND [date] > IFNULL(
        (SELECT MAX([date]) FROM [{dst_table}]
        WHERE [uid] = '{uid}' AND [dtype] = 124),
        '1900-01-01')"""


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
        mapping = {v.name: v for v in YahooFinancialsMapping}

        while data:
            item = data.pop(0)

            # Map the field
            field = mapping.get(item[2], None)
            if field is None:
                continue

            if field.code == '':
                continue

            # Adjust the date
            dt = item[3] - off.BDay(10)
            ref = off.BMonthEnd().rollforward(dt)

            # Divide to millions
            value = item[5] * field.mult

            # Build the new tuple
            data_ins.append(
                (item[0], field.code, ref.strftime('%Y-%m-%d'), item[4], value)
            )

        return data_ins


class DividendsItem(BaseImportItem):
    _Q_READWRITE = """
    INSERT OR REPLACE INTO [{dst_table}] ([uid], [dtype], [date], [value])
    SELECT '{uid}', 621, [date], [value]
    FROM [YahooDividends] WHERE [ticker] = ?"""
    _Q_INCR = """ AND [date] > IFNULL(
        (SELECT MAX([date]) FROM [{dst_table}]
        WHERE [uid] = '{uid}' AND [dtype] = 621),
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

    @staticmethod
    def _clean_data(data: list[tuple], *args) -> list[tuple]:
        """ Prepare results for import. """
        data_ins = []
        while data:
            item = data.pop(0)

            # Calculate the factor
            ratio = str(item[2]).split(':')
            value = float(ratio[1]) / float(ratio[0])

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
    _BASE_URL = u"https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{}"
    _TABLE = "YahooFinancials"
    _PARAMS = {
        'type': DwnParameter('type', True, None),
        'period1': DwnParameter('period1', True, 493590046),
        'period2': DwnParameter('period2', True, None),
        'merge': DwnParameter('merge', False, False),
        'padTimeSeries': DwnParameter('padTimeSeries', False, False),
        'lang': DwnParameter('lang', False, 'en-US'),
        'region': DwnParameter('region', False, 'US'),
        'corsDomain': DwnParameter('corsDomain', True, 'finance.yahoo.com'),
    }

    def _set_default_params(self) -> None:
        n = len(YahooFinancialsDownloadList) // 2
        keys_list = [
            [f'annual{key}' for key in YahooFinancialsDownloadList[:n]],
            [f'annual{key}' for key in YahooFinancialsDownloadList[n:]],
            [f'quarterly{key}' for key in YahooFinancialsDownloadList[:n]],
            [f'quarterly{key}' for key in YahooFinancialsDownloadList[n:]]
        ]

        # Calculate the dates
        # ld = self._fetch_last_data_point((self.ticker,))
        ld = self._DATE0
        period1 = int(pd.to_datetime(ld).value / 1e9)
        period2 = int(time.time())

        # Collect defaults
        defaults = {}
        for p in self._PARAMS.values():
            if p.default is not None:
                defaults[p.code] = p.default

        # Go through the parameters
        for keys in keys_list:
            d = defaults.copy()
            d.update(
                {
                    'type': ','.join(keys),
                    'period1': period1,
                    'period2': period2,
                }
            )
            self._p.append(d)

    def _local_initializations(self, ext_p: dict) -> None:
        """ Local initializations for the single page. """
        pass

    def _parse(self) -> None:
        """ Parse the fetched object. """
        all_keys = {v.name: v.statement for v in YahooFinancialsMapping}
        data = []

        for json_data in self._robj:
            js = json.loads(json_data.text)
            result = js['timeseries']['result']

            if 'annual' in result[0]['meta']['type'][0]:
                freq = 'A'
            elif 'quarterly' in result[0]['meta']['type'][0]:
                freq = 'Q'
            else:
                raise Ex.NoNewDataWarning(f'YahooDownloader(): {self._ticker} | no new data downloaded')

            # data = []
            key_copy = all_keys.copy()
            for r in result:
                prefixed_code = r['meta']['type'][0]
                if prefixed_code in r:
                    entries = r[prefixed_code]
                    code = prefixed_code.removeprefix('annual').removeprefix('quarterly')
                    sheet = key_copy.pop(code)
                    for entry in entries:
                        data.append((
                            self._ticker, freq,
                            entry.get('currencyCode', None),
                            sheet,
                            entry['asOfDate'],
                            code,
                            entry['reportedValue']['raw']
                        ))

        self._res = pd.DataFrame(data, columns=self._COLUMNS)


class YahooHistoricalBasePage(YahooBasePage):
    """ Base page for historical downloads. """
    _PARAMS = {
        'period1': DwnParameter('period1', True, None),
        'period2': DwnParameter('period2', True, None),
        'interval': DwnParameter('interval', False, '1d'),
        'events': DwnParameter('events', False, None),
        'crumb': DwnParameter('crumb', False, None),
    }
    _BASE_URL = u"https://query1.finance.yahoo.com/v7/finance/download/{}?"
    _SKIP = [1]

    @property
    @abstractmethod
    def event(self) -> str:
        """ Return the event to complete the request url. """

    def _set_default_params(self) -> None:
        ld = self._fetch_last_data_point((self._ticker,))
        # We add 2 days instead of 1 since with 1 day of offset the previous
        # split is downloaded again
        start = pd.to_datetime(ld) + pd.DateOffset(days=2)
        period1 = str(int(start.timestamp()))
        period2 = Cal.today(mode='str', fmt='%s')

        # Collect defaults
        defaults = {}
        for p in self._PARAMS.values():
            if p.default is not None:
                defaults[p.code] = p.default

        # Go through the parameters
        defaults.update(
            {
                'period1': period1,
                'period2': period2,
            }
        )
        self._p = [defaults]

    def _local_initializations(self, ext_p: dict) -> None:
        """ Local initializations for the single page. """
        p = {'events': self.event}

        translate = {'start': 'period1', 'end': 'period2'}
        for ext_k, ext_v in ext_p.items():
            if ext_k in translate:
                p[translate[ext_k]] = str(int(pd.to_datetime(ext_v).timestamp()))

        self._p[0].update(p)

    def _parse_csv(self) -> pd.DataFrame:
        df = pd.read_csv(
            StringIO(self._robj[0].text),
            sep=',',
            header=None,
            names=self._COLUMNS,
            skiprows=1
        )

        if df.empty:
            raise Ex.NoNewDataWarning(f'{self._ticker} | no new data downloaded')

        # When downloading prices the oldest row is often made of nulls,
        # this is to remove it
        df.replace(to_replace='null', value=np.nan, inplace=True)
        df.dropna(subset=self._COLUMNS[1:], inplace=True)
        df.insert(0, 'ticker', self._ticker)
        return df


class HistoricalPricesPage(YahooHistoricalBasePage):
    """ Download historical prices. """
    _PAGE = 'HistoricalPrices'
    _COLUMNS = YahooHistPricesConf
    _TABLE = 'YahooPrices'
    _Q_MAX_DATE = "select max(date) from YahooPrices where ticker = ?"
    _Q_SELECT = "select * from YahooPrices where ticker = ?"

    @property
    def event(self) -> str:
        return "history"

    def _set_default_params(self) -> None:
        ld = self._fetch_last_data_point((self._ticker,))
        period1 = str(int(pd.to_datetime(ld).timestamp()))
        period2 = Cal.today(mode='str', fmt='%s')

        # Collect defaults
        defaults = {}
        for p in self._PARAMS.values():
            if p.default is not None:
                defaults[p.code] = p.default

        # Go through the parameters
        defaults.update(
            {
                'period1': period1,
                'period2': period2,
            }
        )
        self._p = [defaults]

    def _parse(self) -> None:
        """ Parse the fetched object. """
        self._res = self._parse_csv()


class DividendsPage(YahooHistoricalBasePage):
    """ Download historical dividends. """
    _PAGE = 'Dividends'
    _COLUMNS = YahooHistDividendsConf
    _TABLE = 'YahooDividends'
    _Q_MAX_DATE = "select max(date) from YahooDividends where ticker = ?"
    _Q_SELECT = "select * from YahooDividends where ticker = ?"

    @property
    def event(self) -> str:
        return "div"

    def _parse(self) -> None:
        """ Parse the fetched object. """
        self._res = self._parse_csv()


class SplitsPage(YahooHistoricalBasePage):
    """ Download historical splits. """
    _PAGE = 'Splits'
    _COLUMNS = YahooHistSplitsConf
    _TABLE = 'YahooSplits'
    _Q_MAX_DATE = "select max(date) from YahooSplits where ticker = ?"
    _Q_SELECT = "select * from YahooSplits where ticker = ?"

    @property
    def event(self) -> str:
        return "split"

    def _parse(self) -> None:
        """ Parse the fetched object. """
        df = self._parse_csv()

        Ut.print_wrn(
            Ex.NoNewDataWarning(
                f' >>> New split found for {self._ticker}!\n{df.to_string}'
            )
        )

        self._res = df


class ChartPage(YahooHistoricalBasePage):

    _PAGE = 'Chart'
    _BASE_URL = u"https://query2.finance.yahoo.com/v8/finance/chart/{}?"
    _COLUMNS = [YahooHistPricesConf, YahooHistDividendsConf, YahooHistSplitsConf]
    _Q_MAX_DATE = "select max(date) from YahooDividends where ticker = ?"
    _DATE0 = '2024-07-01'  # FIXME: REMOVE!!!
    _TABLE = ['YahooPrices', 'YahooDividends', 'YahooSplits']
    _PARAMS = {
        'period1': DwnParameter('period1', True, None),
        'period2': DwnParameter('period2', True, None),
        'interval': DwnParameter('interval', False, '1d'),
        'events': DwnParameter('events', False, None),
        'crumb': DwnParameter('crumb', False, None),
    }

    @property
    def event(self) -> str:
        return "div,split,capitalGains"

    def _parse(self) -> None:
        j = json.loads(self._robj[0].text)
        chart = j['chart']
        if chart['error']:
            raise Ex.DownloaderError(f'{self._ticker} | Error: {chart["error"]}')
        result = chart['result'][0]

        # Build up the historical prices table
        timestamps = (pd.to_datetime(result['timestamp'], unit='s')
                      .strftime('%Y-%m-%d')
                      .to_numpy())
        ohlcv = result['indicators']['quote'][0]
        openp = pd.Series(ohlcv['open']).round(2)
        high = pd.Series(ohlcv['high']).round(2)
        low = pd.Series(ohlcv['low']).round(2)
        close = pd.Series(ohlcv['close']).round(2)
        volume = pd.Series(ohlcv['volume']).astype('Int64')
        adj_close = pd.Series(result['indicators']['adjclose'][0]['adjclose']).round(2)

        dividends_data = None
        splits_data = None
        events = result.get('events', None)
        if events:

            # Build dividends table
            dividends = events.get('dividends', None)
            if dividends:
                dividends_data = [
                    (
                        pd.to_datetime(d['date'], unit='s').strftime('%Y-%m-%d'),
                        d['amount']
                    )
                    for d in dividends.values()
                ]

            # Build splits table
            splits = events.get('splits', None)
            if splits:
                splits_data = [
                    (
                        pd.to_datetime(s['date'], unit='s').strftime('%Y-%m-%d'),
                        s['splitRatio']
                    )
                    for s in splits.values()
                ]

        # Build capital gains table
        # TODO: implement capital gains

        # Dataframe prices
        df_p = pd.DataFrame(columns=self._COLUMNS[0])
        df_p['date'] = timestamps
        df_p['open'] = openp
        df_p['high'] = high
        df_p['low'] = low
        df_p['close'] = close
        df_p['adj_close'] = adj_close
        df_p['volume'] = volume
        df_p.replace(to_replace='null', value=np.nan, inplace=True)
        df_p.dropna(subset=['close'], inplace=True)
        df_p.insert(0, 'ticker', self._ticker)

        # Dataframe dividends
        df_d = pd.DataFrame(dividends_data, columns=self._COLUMNS[1])
        df_d.replace(to_replace='null', value=np.nan, inplace=True)
        df_d.insert(0, 'ticker', self._ticker)

        # Dataframe splits
        df_s = pd.DataFrame(splits_data, columns=self._COLUMNS[2])
        df_s.replace(to_replace='null', value=np.nan, inplace=True)
        df_s.insert(0, 'ticker', self._ticker)

        self._res = (df_p, df_d, df_s)

    def _write_to_db(self) -> None:
        """ Write to the database table. Overridden to write to multiple tables. """

        for i, df in enumerate(self._res):
            # Get all fields and data
            fields_all = df.columns.values.tolist()
            data_all = df.values.tolist()

            # We make the use of UPSERT optional field
            if self.use_upsert:
                # Update/Insert new data
                self._db.executemany(
                    self._qb.upsert(
                        self._TABLE[i],
                        fields=fields_all
                    ),
                    data_all,
                    commit=True
                )
            else:
                # Delete old data
                keys = [k for k in self._qb.get_keys(self._TABLE[i])]
                self._db.executemany(
                    self._qb.delete(
                        self._TABLE[i],
                        fields=keys
                    ),
                    df[keys].values.tolist(),
                    commit=False
                )

                # Insert new data
                self._db.executemany(
                    self._qb.merge(
                        self._TABLE[i],
                        ins_fields=fields_all
                    ),
                    data_all,
                    commit=True
                )

        self._is_saved = True


