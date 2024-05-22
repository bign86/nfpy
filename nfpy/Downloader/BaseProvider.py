#
# Base class for Import items
# Base class to handle imports
#

from abc import (ABCMeta, abstractmethod)
from enum import Enum

import nfpy.Calendar as Cal
from nfpy.DatatypeFactory import get_dt_glob
import nfpy.DB as DB
import nfpy.IO.Utilities as Ut
import nfpy.Tools.Utilities as Uti


class BaseProvider(metaclass=ABCMeta):
    """ Base class for providers. """

    _PROVIDER = ''

    def __init__(self):
        self._today = Cal.today(mode='date')

    @staticmethod
    def _generate(todo: set):
        for d in todo:
            symbol = '.' + '.'.join([d.provider, d.page + 'Page'])
            class_ = Uti.import_symbol(symbol, pkg='nfpy.Downloader')
            yield d, class_(d.ticker, d.currency)

    def get_download_generator(
        self,
        downloads: list | tuple,
        override_date: bool = False
    ) -> tuple:
        # Filter out items to not download due to the date
        if not override_date:
            n = 0
            todo = set()
            for d in downloads:
                n += 1
                if not d.last_update:
                    todo.add(d)
                else:
                    delta_days = (self._today - d.last_update).days
                    if delta_days >= int(d.update_frequency):
                        todo.add(d)
        else:
            todo = set(downloads)
            n = len(todo)

        Ut.print_header(f'\n|  Downloading {self._PROVIDER}  |')
        todo = self._filter_todo_downloads(todo)
        skipped = n - len(todo)
        print(f' > Skipped {skipped} items')

        return skipped, self._generate(todo)

    @abstractmethod
    def _filter_todo_downloads(self, todo: set) -> set:
        """ Apply provider-specific filtering. """


def get_provider(provider: str) -> BaseProvider:
    symbol = '.' + '.'.join([provider, provider + 'Provider'])
    return Uti.import_symbol(symbol, pkg='nfpy.Downloader')


class Action(Enum):
    DEL = 0
    RDW = 1
    INC = 2


class BaseImportItem(metaclass=ABCMeta):
    """ Base class for import items. """

    _MODE = 'RW'
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

    @staticmethod
    def _clean_data(data: list[tuple]) -> list[tuple]:
        """ Prepare results for import. """
        return data

    def run(self) -> None:
        params = self._get_params()

        if self._MODE == 'RW':
            qrw = self._Q_READWRITE
            if self._incr:
                qrw += self._Q_INCR
            qrw = qrw.format(**self._d) + ";"
            self._db.execute(qrw, params, commit=True)

        else:
            qr = self._Q_READ
            if self._incr:
                qr += self._Q_INCR
            qr = qr.format(**self._d) + ';'

            data = self._db.execute(qr, params).fetchall()
            data_clean = self._clean_data(data)

            if len(data_clean) > 0:
                self._db.executemany(
                    self._Q_WRITE.format(**self._d),
                    data_clean,
                    commit=True
                )
