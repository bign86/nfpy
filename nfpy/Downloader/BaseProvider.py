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
    _CLEAN_F = ()

    def __init__(self, item: dict):
        self._db = DB.get_db_glob()
        self._dt = get_dt_glob()
        self._d = item

    def _get_params(self) -> tuple:
        """ Return the correct parameters for the read query. """
        return self._d['ticker'].split('/')[0],

    def _clean_routines(self, data: list) -> None:
        for cr in self._CLEAN_F:
            cr(data)

    def run(self) -> None:
        qr = self._Q_READ.format(**self._d)
        params = self._get_params()
        data = self._db.execute(qr, params).fetchall()

        self._clean_routines(data)

        qw = self._Q_WRITE.format(**self._d)
        self._db.executemany(qw, data, commit=True)


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

    def get_import_item(self, data: dict) -> BaseImportItem:
        asset = self._af.get(data['uid'])
        if asset.type == 'Company':
            data['dst_table'] = asset.constituents_table
        else:
            data['dst_table'] = asset.ts_table
        return self._IMPORT_ITEMS[data['item']](data)
