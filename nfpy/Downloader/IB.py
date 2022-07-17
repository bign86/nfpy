#
# Interactive Brokers Downloader
# Downloads data from Interactive Brokers API
#

import datetime
import pandas as pd
from time import sleep
import xml.etree.ElementTree as ET

from nfpy.Tools.Configuration import get_conf_glob

from .BaseDownloader import BasePage
from .BaseProvider import BaseImportItem
from .DownloadsConf import IBFundamentalsConf
from .IBApp import *


class FinancialsItem(BaseImportItem):
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
    def _clean_eoy_dates(data: list[tuple]) -> list[tuple]:
        """ Moves EOY results to the actual end of the year. """
        data_ins = []
        while data:
            item = data.pop(0)
            if (item[3] == 'A') & (item[2].month != 12):
                new_date = datetime.date(item[2].year - 1, 12, 31)
                item = (item[0], item[1], new_date, item[3], item[4])

            data_ins.append(item)

        return data_ins

    def run(self) -> None:
        params = self._get_params()

        qr = self._Q_READ
        if self._incr:
            qr += self._Q_INCR
        qr = qr.format(**self._d) + ';'

        data = self._db.execute(qr, params).fetchall()

        if len(data) > 0:
            self._db.executemany(
                self._Q_WRITE.format(**self._d),
                self._clean_eoy_dates(data),
                commit=True
            )


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
