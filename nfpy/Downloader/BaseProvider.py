#
# Base class for Providers
# Base class to handle the single provider
#

from abc import ABCMeta

from nfpy.Assets import get_af_glob
import nfpy.DB as DB
from nfpy.DatatypeFactory import get_dt_glob
from nfpy.Tools import Utilities as Ut

from .BaseDownloader import BasePage


class BaseImportItem(object):
    """ Base class for import items. """

    _Q_READ = ''
    _Q_WRITE = ''
    _Q_READWRITE = ''
    _Q_INCR = ''

    def __init__(self, item: dict, incr: bool):
        self._db = DB.get_db_glob()
        self._dt = get_dt_glob()
        self._d = item
        self._incr = incr

    def _get_params(self) -> tuple:
        """ Return the correct parameters for the read query. """
        return self._d['ticker'],

    def run(self) -> None:
        params = self._get_params()

        qrw = self._Q_READWRITE
        if self._incr:
            qrw += self._Q_INCR
        qrw = qrw.format(**self._d) + ';'
        self._db.execute(qrw, params, commit=True)


class BaseProvider(metaclass=ABCMeta):
    """ Base metaclass for providers. Every provider must be derived from this
        base class overwriting everything required to specify a single provider.
        The class contains the pages and database tables used by the provider,
        specific functions and information.
    """

    _PROVIDER = ''
    _PAGES = {}
    _IMPORT_ITEMS = {}
    _FINANCIALS_MAP = []

    def __init__(self):
        # This is required just to get the asset elaboration table
        self._af = get_af_glob()

    @property
    def pages(self):
        return self._PAGES.keys()

    def create_page_obj(self, page: str, ticker: str) -> BasePage:
        if page not in self._PAGES:
            raise ValueError("Page {} not available for {}"
                             .format(page, self._PROVIDER))
        symbol = '.' + '.'.join([self._PROVIDER, self._PAGES[page]])
        class_ = Ut.import_symbol(symbol, pkg='nfpy.Downloader')
        return class_(ticker)

    def get_import_item(self, data: dict, incremental: bool) -> BaseImportItem:
        asset = self._af.get(data['uid'])
        if asset.type == 'Company':
            data['dst_table'] = asset.constituents_table
        else:
            data['dst_table'] = asset.ts_table
        return self._IMPORT_ITEMS[data['item']](data, incremental)
