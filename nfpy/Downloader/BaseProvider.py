#
# Base class for Providers
# Base class to handle the single provider
#

from abc import ABCMeta, abstractmethod
from typing import Sequence

from nfpy.Assets import get_af_glob
from nfpy.DB import (get_db_glob, get_qb_glob)
from nfpy.Downloader.BaseDownloader import BasePage
from nfpy.Handlers.DatatypeFactory import get_dt_glob
from nfpy.Tools.Utilities import import_symbol


class BaseProvider(metaclass=ABCMeta):
    """ Base metaclass for providers. Every provider must be derived from this
        base class overwriting everything required to specify a single provider.
        The class contains the pages and database tables used by the provider,
        specific functions and information.
    """

    _PROVIDER = ''
    _PAGES = {}
    _TABLES = {}
    _FINANCIALS_MAP = []

    def __init__(self):
        self._db = get_db_glob()
        self._qb = get_qb_glob()
        self._dt = get_dt_glob()
        # This is required just to get the asset elaboration table
        self._af = get_af_glob()

    @property
    def pages(self):
        return self._PAGES.keys()

    @property
    def tables(self):
        return self._TABLES.keys()

    def create_page_obj(self, page: str) -> BasePage:
        if page not in self._PAGES:
            raise ValueError("Page {} not available for {}".format(page, self._PROVIDER))
        symbol = '.'.join(['nfpy.Downloader', self._PROVIDER, self._PAGES[page]])
        class_ = import_symbol(symbol)
        return class_()

    def do_import(self, data: dict):
        """ Generates the query for the import and execute the data transfer.

            Input:
                data [dict]: data from the Imports table
        """
        query, params = self.get_import_data(data)
        # print(query, params)
        # TODO: break the query in two parts and run data cleaning routines
        self._db.execute(query, params, commit=True)

    @staticmethod
    @abstractmethod
    def create_input_dict(last_date: str) -> dict:
        """ Input creation specific for each provider. """

    @abstractmethod
    def get_import_data(self, data: dict) -> Sequence[Sequence]:
        """ Get information to perform importing. """
