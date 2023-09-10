#
# Interactive Brokers Downloader
# Downloads data from Interactive Brokers API
#

import pandas as pd
import pandas.tseries.offsets as off
from time import sleep
import xml.etree.ElementTree as ET

from nfpy.Tools import (get_conf_glob, Utilities as Ut)

from .BaseDownloader import BasePage
from .BaseProvider import BaseImportItem
from .DownloadsConf import (IBFinancialsConf, IBFinancialsMapping)
from .IBApp import *


class FinancialsItem(BaseImportItem):
    _MODE = 'SPLIT'
    _Q_READ = """select distinct '{uid}', statement, code, date, freq, value
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

            # Map the field
            try:
                field = IBFinancialsMapping[item[1]][item[2]]
            except KeyError as ex:
                Ut.print_exc(ex)
                continue

            # Adjust the date
            dt = item[3] - off.BDay(10)
            ref = off.BMonthEnd().rollforward(dt)

            value = item[5] * field[2]

            # Build the new tuple
            data_ins.append(
                (item[0], item[2], ref.strftime('%Y-%m-%d'), item[4], value)
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
        data = self._app.return_data
        self._robj = data if data is not None else []


class FinancialsPage(IBBasePage):
    _PAGE = 'Financials'
    _COLUMNS = IBFinancialsConf
    _TABLE = 'IBFinancials'

    def _local_initializations(self, ext_p: dict) -> None:
        """ Local initializations for the single page. """
        tck = self._ticker.split('/')
        self._app = IBAppFundamentals("ReportsFinStatements")
        self._app.addContracts(tck, ext_p['currency'])
        self._p.append(ext_p)

    def _parse(self) -> None:
        tree = ET.fromstring(self._robj)
        financial = tree.find('FinancialStatements')

        tck = self._ticker.split('/')[0]
        ccy = self._p[0]['currency']

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
