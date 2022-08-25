#
# Interactive Brokers Downloader
# Downloads data from Interactive Brokers API
#

import pandas as pd
import pandas.tseries.offsets as off
from time import sleep
import xml.etree.ElementTree as ET

from nfpy.Tools import get_conf_glob

from .BaseDownloader import BasePage
from .BaseProvider import BaseImportItem
from .DownloadsConf import IBFundamentalsConf
from .IBApp import *


class FinancialsItem(BaseImportItem):
    _MODE = 'SPLIT'
    _Q_READ = """select distinct '{uid}', code, date, freq, value
    from IBFinancials where ticker = ?"""
    _Q_WRITE = """insert or replace into {dst_table}
    (uid, code, date, freq, value) values (?, ?, ?, ?, ?)"""
    _Q_INCR = """ and date > ifnull((select max(date) from {dst_table}
    where uid = '{uid}'), '1900-01-01')"""

    def _get_params(self) -> tuple[str]:
        """ Return the correct parameters for the read query. """
        return self._d['ticker'].split('/')[0],

    @staticmethod
    def _clean_data(data: list[tuple]) -> list[tuple]:
        """ Prepare results for import. """
        data_ins = []
        while data:
            item = data.pop(0)

            # Adjust the date
            dt = item[2]
            if dt.month == 1:
                month = 1
            elif 2 <= dt.month <= 4:
                month = 4
            elif 5 <= dt.month <= 7:
                month = 7
            elif 8 <= dt.month <= 10:
                month = 10
            else:
                month = 1
            ref = pd.Timestamp(dt.year, month, 1) - off.BDay(1)

            # Build the new tuple
            data_ins.append(
                (item[0], item[1], ref.strftime('%Y-%m-%d'), item[3], item[4])
            )

        return data_ins


class IBBasePage(BasePage):
    """ Base class for all Interactive Brokers downloads. It cannot be used by
        itself but the derived classes for single download instances should
        always be used.
    """

    _ENCODING = 'utf-8-sig'
    _PROVIDER = 'IB'
    _SLEEP_TIME = 3

    def __init__(self, ticker: str):
        super().__init__(ticker)
        self._conf = get_conf_glob()
        self._app = None

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return ''

    def _set_default_params(self) -> None:
        pass

    def _download(self) -> None:
        """ Run the app instead of downloading. """
        self._app.connect(
            self._conf.ib_interface,
            self._conf.ib_tws_port,
            self._conf.ib_client_id
        )
        self._app.run()
        sleep(self._SLEEP_TIME)
        self._robj = self._app.return_data


class FinancialsPage(IBBasePage):
    _PAGE = 'Financials'
    _COLUMNS = IBFundamentalsConf
    _TABLE = 'IBFinancials'

    def _local_initializations(self) -> None:
        """ Local initializations for the single page. """
        tck = self.ticker.split('/')
        self._app = IBAppFundamentals("ReportsFinStatements")
        self._app.addContracts(tck, self._ext_p['currency'])

    def _parse(self) -> None:
        tree = ET.fromstring(self._robj)
        financial = tree.find('FinancialStatements')

        tck = self.ticker.split('/')[0]
        ccy = self._ext_p['currency']

        data = []
        for freq in ('AnnualPeriods', 'InterimPeriods'):
            f_ = 'A' if freq == 'AnnualPeriods' else 'Q'
            history = financial.find(freq)
            for period in history.findall('FiscalPeriod'):
                dt_ = period.get('EndDate')
                for statement in period.findall('Statement'):
                    st_ = statement.get('Type')
                    for item in statement.findall('lineItem'):
                        cd_ = item.get('coaCode')
                        data.append((tck, f_, dt_, ccy, st_, cd_, item.text))

        self._res = pd.DataFrame(data, columns=self._COLUMNS)


class EPSPage(IBBasePage):
    _PAGE = 'EPS'
    _COLUMNS = IBFundamentalsConf
    _TABLE = ''

    def _local_initializations(self) -> None:
        """ Local initializations for the single page. """
        tck = self.ticker.split('/')
        self._app = IBAppFundamentals("ReportsFinSummary")
        self._app.addContracts(tck, self._ext_p['currency'])

    def _parse(self) -> None:
        tree = ET.fromstring(self._robj)
        print(self._robj)

        self._res = pd.DataFrame([], columns=self._COLUMNS)


class RatiosPage(IBBasePage):
    _PAGE = 'Ratios'
    _COLUMNS = IBFundamentalsConf
    _TABLE = ''

    def _local_initializations(self) -> None:
        """ Local initializations for the single page. """
        tck = self.ticker.split('/')
        self._app = IBAppFundamentals("ReportRatios")
        self._app.addContracts(tck, self._ext_p['currency'])

    def _parse(self) -> None:
        tree = ET.fromstring(self._robj)
        print(self._robj)

        self._res = pd.DataFrame([], columns=self._COLUMNS)
