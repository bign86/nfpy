#
# DB connection functions
#

import os
import atexit
import sqlite3
from typing import Iterable

import pandas as pd

from nfpy.Configuration import get_conf_glob
from nfpy.Tools import (Singleton, Exceptions as Ex)

# Conversion between db types and python types
SQLITE2PY_TYPES = {
    'TEXT': str,
    'INT': int,
    'INTEGER': int,
    'FLOAT': float,
    'REAL': float,
    'NUMERIC': int,
    'DATE': pd.Timestamp,
    'DATETIME': pd.Timestamp,
    'BOOL': bool,
}

_MIN_DB_VERSION = 0.7


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
    def db_path(self, v: str):
        self._db_path = str(v)
        self._create_connection()

    @db_path.deleter
    def db_path(self):
        self._db_path = None
        self._close_connection()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    @connection.deleter
    def connection(self):
        self._close_connection()

    @property
    def cursor(self) -> sqlite3.Cursor:
        return self.connection.cursor()

    def execute(self, q: str, p: Iterable = None, commit: bool = False)\
            -> sqlite3.Cursor:
        # print('Exec: {}'.format(q))
        c = self.cursor
        try:
            if p:
                c.execute(q, p)
            else:
                c.execute(q)
            if commit:
                self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
            raise
        return c

    def executemany(self, q: str, p: Iterable, commit: bool = False)\
            -> sqlite3.Cursor:
        c = self.cursor
        try:
            c.executemany(q, p)
            if commit:
                self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
            raise
        return c

    def commit(self):
        try:
            self._conn.commit()
        except sqlite3.Error:
            self._conn.rollback()
            raise

    def rollback(self):
        self._conn.rollback()

    def _create_connection(self):
        """ Creates the DB connection """
        self._conn = sqlite3.connect(self.db_path)

        # Sanity check on the database version
        q = "select value from SystemInfo where field = 'DBVersion'"
        v = self.execute(q).fetchone()[0]
        self._db_version = float(v)
        if v < _MIN_DB_VERSION:
            raise Ex.DatabaseError('DB version {} < {} (minimum version)'
                                   .format(v, _MIN_DB_VERSION))

        self._is_connected = True

    def _close_connection(self):
        """ Close the DB connection """
        if self._is_connected:
            try:
                # call for the optimization of the indexes
                self.cursor.execute('PRAGMA optimize;')
                self._conn.commit()
            except sqlite3.Error:
                self._conn.rollback()
                print('Cannot commit to the database!')
                raise
            else:
                self._conn.close()
                self._conn = None
                self._is_connected = False


def get_db_glob(db_path: str = None) -> DBHandler:
    """ Returns the pointer to the global DB """
    if not db_path:
        db_path = get_conf_glob().db_path
    else:
        if not isinstance(db_path, str):
            raise Ex.DatabaseError("Not a valid database name")
    return DBHandler(db_path)


def backup_db(db_path: str = None, f_name: str = None):
    from datetime import datetime
    from shutil import copyfile

    conf = get_conf_glob()
    if not db_path:
        db_path = conf.db_path
    else:
        if not isinstance(db_path, str):
            raise Ex.DatabaseError("Not a valid database name")

    path, file = os.path.split(db_path)

    if f_name is None:
        bak_path = conf.backup_folder
        name, ext = os.path.splitext(file)
        date = '_' + datetime.today().strftime('%Y%m%d_%H%M%S')
        new_file = os.path.join(bak_path, ''.join([name, date, ext]))
    else:
        new_file = f_name

    copyfile(db_path, new_file)
    print("Database backup'd in: {}".format(new_file))


# register the connection closing.
atexit.register(get_db_glob()._close_connection)
