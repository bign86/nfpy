#
# DB connection functions
#

import os
import atexit
from typing import (Iterable, Optional)

# from ..DB import logger
from nfpy.Tools import (Singleton, Exceptions as Ex,
                        get_conf_glob, Utilities as Ut)

from .DBTypes import *

_MIN_DB_VERSION = 1.02


class DBHandler(metaclass=Singleton):
    """ Base class for DB connection. """

    def __init__(self, db_path: str):
        self._db_path = str(db_path)
        self._conn = None
        self._is_connected = False
        self._db_version = None
        self._create_connection()

    def __bool__(self):
        return self._is_connected

    __nonzero__ = __bool__

    @property
    def version(self) -> float:
        return self._db_version

    @property
    def db_path(self) -> str:
        return self._db_path

    @db_path.setter
    def db_path(self, v: str) -> None:
        self._db_path = str(v)
        self._create_connection()

    @db_path.deleter
    def db_path(self) -> None:
        self._db_path = None
        self._close_connection()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    @connection.deleter
    def connection(self) -> None:
        self._close_connection()

    @property
    def cursor(self) -> sqlite3.Cursor:
        return self.connection.cursor()

    def execute(self, q: str, p: Iterable = (), commit: bool = False) \
            -> sqlite3.Cursor:
        c = self.cursor
        try:
            c.execute(q, tuple(p))
            if commit:
                self.connection.commit()
        except sqlite3.Error as ex:
            msg = f'{ex}\n{q}\n{repr(p)}'
            Ut.print_exc(Ex.DatabaseError(msg))
            self.connection.rollback()
            raise ex
        return c

    def executemany(self, q: str, p: Iterable, commit: bool = False) \
            -> sqlite3.Cursor:
        c = self.cursor
        try:
            c.executemany(q, tuple(p))
            if commit:
                self.connection.commit()
        except sqlite3.Error as ex:
            msg = f'{ex}\n{q}\n{repr(p)}'
            Ut.print_exc(Ex.DatabaseError(msg))
            self.connection.rollback()
            raise ex
        return c

    def commit(self) -> None:
        try:
            self._conn.commit()
        except sqlite3.Error as ex:
            self._conn.rollback()
            raise ex

    def rollback(self) -> None:
        self._conn.rollback()

    def _create_connection(self) -> None:
        """ Creates the DB connection """
        self._conn = get_db_connection(self.db_path)

        # Sanity check on the database version
        q = "select value from SystemInfo where field = 'DBVersion'"
        v = self.execute(q).fetchone()[0]
        self._db_version = float(v)
        if v < _MIN_DB_VERSION:
            msg = f'DB version {v} < {_MIN_DB_VERSION} (minimum version)'
            # logger.error(msg)
            raise Ex.DatabaseError(msg)

        # logger.info('DB version {}'.format(v))
        self._is_connected = True

    def _close_connection(self) -> None:
        """ Close the DB connection """
        if self._is_connected:
            try:
                # call for the optimization of the indexes
                self.cursor.execute('PRAGMA optimize;')
                self._conn.commit()
            except sqlite3.Error as ex:
                self._conn.rollback()
                print('Cannot commit to the database!')
                raise ex
            else:
                self._conn.close()
                self._conn = None
                self._is_connected = False

    def backup(self, f_name: Optional[str] = None) -> None:
        """ Backup the connected database into the destination. """
        # Create new backup filename
        path, file = os.path.split(self._db_path)
        if f_name is None:
            name, ext = os.path.splitext(file)
            new_file = os.path.join(
                get_conf_glob().backup_folder,
                ''.join([name, f"_{datetime.today().strftime('%Y%m%d_%H%M%S')}", ext])
            )
        else:
            new_file = f_name

        # Visualize progress
        def progress(status, remaining, total):
            print(f'Copied {total - remaining} of {total} pages...')

        try:
            bck = sqlite3.connect(new_file)
            self._conn.backup(bck, pages=1, progress=progress)
            bck.close()
        except sqlite3.Error as ex:
            Ut.print_exc(ex)
            raise ex

        print(f"Database backup'd in: {new_file}")


def get_db_connection(path: str) -> sqlite3.Connection:
    return sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)


def get_db_glob(db_path: Optional[str] = None) -> DBHandler:
    """ Returns the pointer to the global DB """
    if not db_path:
        db_path = get_conf_glob().db_path
    else:
        if not isinstance(db_path, str):
            raise Ex.DatabaseError("Not a valid database name")
    return DBHandler(db_path)


def backup_db(db_path: Optional[str] = None,
              f_name: Optional[str] = None) -> None:
    from shutil import copyfile

    conf = get_conf_glob()
    if not db_path:
        db_path = conf.db_path
    else:
        if not isinstance(db_path, str):
            raise Ex.DatabaseError("Not a valid database name")

    path, file = os.path.split(db_path)

    if f_name is None:
        name, ext = os.path.splitext(file)
        new_file = os.path.join(
            conf.backup_folder,
            ''.join([name, f"_{datetime.today().strftime('%Y%m%d_%H%M%S')}", ext])
        )
    else:
        new_file = f_name

    os.makedirs(conf.backup_folder)
    copyfile(db_path, new_file)
    print(f"Database backup'd in: {new_file}")


# register the connection closing.
atexit.register(get_db_glob()._close_connection)
