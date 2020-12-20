#
# Interactive Brokers Downloader
# Downloads data from Interactive Brokers API
#

import pandas as pd
from time import sleep
from typing import Dict, Sequence
import xml.etree.ElementTree as ET

from nfpy.Configuration import get_conf_glob

from .BaseDownloader import BasePage
from .BaseProvider import BaseProvider
from .DownloadsConf import IBFundamentalsConf
from .IBApp import *


class IBProvider(BaseProvider):
    """ Class for the Interactive Brokers provider. """

    _PROVIDER = 'IB'
    _PAGES = {"Financials": "IBFundamentals"}
    _TABLES = {"Financials": "IBFinancials"}
    _Q_IMPORT_FINAN = """insert or replace into {dst} (uid, code, date, freq, value)
    select distinct '{uid}', ib.code, ib.date, ib.freq, ib.value from {src} as ib
    where ib.ticker = ?;"""

    @staticmethod
    def create_input_dict(last_date: str) -> dict:
        return {}

    def get_import_data(self, data: dict) -> Sequence[Sequence]:
        page = data['page']
        tck = data['ticker'].split('/')[0]
        uid = data['uid']
        t_src = self._TABLES[page]

        if page == 'Financials':
            t_dst = self._af.get(data['uid']).constituents_table
            query = self._Q_IMPORT_FINAN.format(**{'dst': t_dst, 'src': t_src,
                                                   'uid': uid})
            params = (tck,)
        else:
            raise ValueError('Page {} for provider IB unrecognized'.format(page))

        return query, params


class IBBasePage(BasePage):
    """ Base class for all Interactive Brokers downloads. It cannot be used by
        itself but the derived classes for single download instances should
        always be used.
    """

    _ENCODING = 'utf-8-sig'
    _PROVIDER = 'IB'
    _SLEEP_TIME = 5

    def __init__(self, p: Dict = None):
        super().__init__(p)
        self._conf = get_conf_glob()
        self._app = None

    @property
    def baseurl(self) -> str:
        """ Return the base url for the page. """
        return ''  # self._BASE_URL + self._URL_SUFFIX

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

    def _local_initializations(self):
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
