#
# Interactive Brokers Downloader
# Downloads data from Interactive Brokers API
#

import pandas as pd
from time import sleep
import xml.etree.ElementTree as ET

from nfpy.Configuration import get_conf_glob

from .BaseDownloader import BasePage
from .BaseProvider import (BaseProvider, BaseImportItem)
from .DownloadsConf import IBFundamentalsConf
from .IBApp import *


class FinancialsItem(BaseImportItem):
    _Q_READ = """select distinct '{uid}', code, date, freq, value
    from IBFinancials where ticker = ?;"""
    _Q_WRITE = """insert or replace into {dst_table}
    (uid, code, date, freq, value) values (?, ?, ?, ?, ?);"""


class IBProvider(BaseProvider):
    """ Class for the Interactive Brokers provider. """

    _PROVIDER = 'IB'
    _PAGES = {'Financials': 'IBFundamentals'}
    _IMPORT_ITEMS = {'Financials': FinancialsItem}


class IBBasePage(BasePage):
    """ Base class for all Interactive Brokers downloads. It cannot be used by
        itself but the derived classes for single download instances should
        always be used.
    """

    _ENCODING = 'utf-8-sig'
    _PROVIDER = 'IB'
    _SLEEP_TIME = 5

    def __init__(self, ticker: str):
        super().__init__(ticker)
        self._conf = get_conf_glob()
        self._app = None

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return ''  # self._BASE_URL + self._URL_SUFFIX

    def _set_default_params(self) -> None:
        pass

    def _download(self):
        """ Run the app instead of downloading. """
        self._app.connect(self._conf.ib_interface, self._conf.ib_tws_port,
                          self._conf.ib_client_id)
        self._app.run()
        sleep(self._SLEEP_TIME)
        self._robj = self._app.return_data


class IBFundamentals(IBBasePage):

    _PAGE = 'Financials'
    _COLUMNS = IBFundamentalsConf
    _TABLE = 'IBFinancials'

    def _local_initializations(self, params: dict):
        """ Local initializations for the single page. """
        tck = self.ticker.split('/')
        self._app = IBAppFundamentals()
        self._app.addContracts(tck, self._curr)

    def _parse(self):
        tree = ET.fromstring(self._robj)
        financial = tree.find('FinancialStatements')

        tck = self.ticker.split('/')[0]
        ccy = self._curr

        data = list()
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
