#
# Base class for Import items
# Base class to handle imports
#

from nfpy.DatatypeFactory import get_dt_glob
import nfpy.DB as DB


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
        qrw = qrw.format(**self._d) + ";"
        self._db.execute(qrw, params, commit=True)
