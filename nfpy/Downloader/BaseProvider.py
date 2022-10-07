#
# Base class for Import items
# Base class to handle imports
#

from enum import Enum

from nfpy.DatatypeFactory import get_dt_glob
import nfpy.DB as DB


class Action(Enum):
    DEL = 0
    RDW = 1
    INC = 2


class BaseImportItem(object):
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
